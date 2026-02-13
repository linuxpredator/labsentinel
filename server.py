# server.py - LabSentinel Python Backend
# Menggantikan PHP backend dengan Flask

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Lokasi fail logo
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')

@app.route('/static/logo.png')
def serve_logo():
    """Serve logo sebagai static file"""
    return send_file(LOGO_PATH, mimetype='image/png')
app.secret_key = os.environ.get('SECRET_KEY', 'labsentinel-s3cret-key-2026')

# Database path - detect PythonAnywhere environment
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    DB_DIR = os.path.join(os.path.expanduser('~'), 'labsentinel_data')
    os.makedirs(DB_DIR, exist_ok=True)
    DB_PATH = os.path.join(DB_DIR, 'lab_system.db')
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lab_system.db')

def get_db():
    """Dapatkan connection ke SQLite database"""
    conn = sqlite3.connect(DB_PATH, timeout=10)  # 10 saat timeout untuk elak lock
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    return conn

def init_db():
    """Initialize database jika belum wujud"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_uuid TEXT UNIQUE NOT NULL,
            pc_hostname TEXT NOT NULL,
            status TEXT DEFAULT 'LOCKED',
            nama_penuh TEXT,
            no_id TEXT,
            no_telefon TEXT,
            ip_address TEXT,
            mac_address TEXT,
            unlock_time DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Migrate: tambah kolum jika belum wujud
    for col in ['ip_address TEXT', 'mac_address TEXT', 'lab_name TEXT', 'last_seen DATETIME', 'pending_command TEXT']:
        try:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {col}")
        except:
            pass

    # Admin users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            assigned_labs TEXT DEFAULT '',
            is_superadmin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Auto-create default superadmin if table is empty
    count = conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
    if count == 0:
        conn.execute(
            "INSERT INTO admin_users (username, password_hash, is_superadmin) VALUES (?, ?, 1)",
            ('admin', generate_password_hash('admin'))
        )
        print("[DB] Default superadmin created: admin/admin")

    conn.commit()
    conn.close()
    print("[DB] Database initialized")

# Initialize database on startup
init_db()

# ==================== HELPERS ====================

def get_current_admin():
    """Dapatkan maklumat admin dari session. Return dict atau None."""
    if 'admin_id' not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM admin_users WHERE id = ?", (session['admin_id'],)).fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def get_admin_labs(admin):
    """Dapatkan senarai lab yang ditugaskan. None = semua (superadmin)."""
    if admin['is_superadmin']:
        return None
    labs_str = admin.get('assigned_labs', '')
    if not labs_str:
        return []
    return [l.strip() for l in labs_str.split(',') if l.strip()]

# ==================== API ENDPOINTS ====================

@app.route('/api.php', methods=['GET', 'POST'])
@app.route('/lab-system/api.php', methods=['GET', 'POST'])
def api():
    """API endpoint - compatible dengan URL lama"""
    action = request.args.get('action', '')

    if action == 'register':
        # Dipanggil oleh PCClient apabila bermula
        uuid = request.form.get('uuid') or request.args.get('uuid', '')
        pc_name = request.form.get('pc_name') or request.args.get('pc_name', 'Unknown PC')
        mac_address = request.form.get('mac_address') or request.args.get('mac_address', '')
        lab_name = request.form.get('lab_name') or request.args.get('lab_name', '')

        # Dapatkan IP address dari request
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()

        if not uuid:
            return jsonify({'error': 'UUID required'})

        try:
            conn = get_db()
            # Hapus sesi lama
            conn.execute("DELETE FROM sessions WHERE pc_hostname = ?", (pc_name,))
            # Daftar sesi baru dengan IP, MAC dan Lab Name
            conn.execute("INSERT INTO sessions (session_uuid, pc_hostname, ip_address, mac_address, lab_name, last_seen) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                        (uuid, pc_name, ip_address, mac_address, lab_name))
            conn.commit()
            conn.close()
            print(f"[API] Registered: {lab_name}/{pc_name} ({uuid[:8]}...) IP={ip_address} MAC={mac_address}")
            return jsonify({'status': 'registered'})
        except Exception as e:
            return jsonify({'error': str(e)})

    elif action == 'check':
        # Dipanggil oleh PCClient berulang kali (Polling)
        uuid = request.args.get('uuid', '')

        conn = get_db()
        row = conn.execute("SELECT status, pending_command FROM sessions WHERE session_uuid = ?",
                          (uuid,)).fetchone()
        if row:
            pending_cmd = row['pending_command']
            # Clear pending_command selepas baca (one-shot delivery)
            conn.execute("UPDATE sessions SET last_seen = CURRENT_TIMESTAMP, pending_command = NULL WHERE session_uuid = ?", (uuid,))
            conn.commit()
        conn.close()

        if row:
            result = {'status': row['status']}
            if pending_cmd:
                result['command'] = pending_cmd
            return jsonify(result)
        else:
            return jsonify({'error': 'Session not found'})

    elif action == 'verify_admin':
        # Dipanggil oleh PCClient untuk sahkan password admin
        if request.method != 'POST':
            return jsonify({'verified': False, 'error': 'POST required'}), 405

        password = request.form.get('password', '')
        lab_name = request.form.get('lab_name', '')

        if not password:
            return jsonify({'verified': False, 'error': 'Password required'})

        conn = get_db()
        users = conn.execute("SELECT * FROM admin_users").fetchall()
        conn.close()

        for user in users:
            if check_password_hash(user['password_hash'], password):
                # Superadmin boleh akses semua makmal
                if user['is_superadmin']:
                    return jsonify({'verified': True, 'admin': user['username']})
                # Admin biasa — semak akses makmal
                assigned = [l.strip() for l in (user['assigned_labs'] or '').split(',') if l.strip()]
                if lab_name in assigned:
                    return jsonify({'verified': True, 'admin': user['username']})

        return jsonify({'verified': False, 'error': 'Password tidak sah atau tiada akses makmal ini'})

    elif action == 'admin_command':
        # Admin remote command — POST sahaja
        if request.method != 'POST':
            return jsonify({'error': 'POST required'}), 405

        # Auth check
        admin = get_current_admin()
        if not admin:
            return jsonify({'error': 'Sila log masuk terlebih dahulu'}), 401

        uuid = request.form.get('uuid', '')
        command = request.form.get('command', '').upper()

        if not uuid or not command:
            return jsonify({'error': 'uuid and command required'})

        # Whitelist validation
        allowed_commands = ('SHUTDOWN', 'RESTART', 'LOCK', 'UNLOCK')
        if command not in allowed_commands:
            return jsonify({'error': f'Invalid command. Allowed: {", ".join(allowed_commands)}'})

        # Lab isolation check for non-superadmin
        admin_labs = get_admin_labs(admin)
        if admin_labs is not None:
            conn = get_db()
            pc = conn.execute("SELECT lab_name FROM sessions WHERE session_uuid = ?", (uuid,)).fetchone()
            conn.close()
            if not pc:
                return jsonify({'error': 'PC not found'}), 404
            if pc['lab_name'] not in admin_labs:
                return jsonify({'error': 'Akses ditolak - PC bukan dalam makmal anda'}), 403

        try:
            conn = get_db()
            if command == 'UNLOCK':
                conn.execute("UPDATE sessions SET pending_command = ?, status = 'UNLOCKED' WHERE session_uuid = ?",
                            (command, uuid))
            elif command == 'LOCK':
                conn.execute("UPDATE sessions SET pending_command = ?, status = 'LOCKED' WHERE session_uuid = ?",
                            (command, uuid))
            else:  # SHUTDOWN / RESTART
                conn.execute("UPDATE sessions SET pending_command = ? WHERE session_uuid = ?",
                            (command, uuid))
            conn.commit()
            conn.close()
            print(f"[ADMIN CMD] {command} → {uuid[:8]}... by {admin['username']}")
            return jsonify({'status': 'ok', 'message': f'{command} sent'})
        except Exception as e:
            return jsonify({'error': str(e)})

    else:
        return jsonify({'error': 'Invalid action'})

@app.route('/unlock.php', methods=['GET', 'POST'])
@app.route('/lab-system/unlock.php', methods=['GET', 'POST'])
def unlock():
    """Unlock page - dengan borang pendaftaran pengguna"""
    import re
    uuid = request.args.get('uuid', '')
    message = ''
    error = ''

    if not uuid:
        return "Invalid Link (No UUID)", 400

    conn = get_db()

    # Handle POST request (Unlock action)
    if request.method == 'POST':
        nama_penuh = request.form.get('nama_penuh', '').strip()
        no_id = request.form.get('no_id', '').strip().upper()
        no_telefon = request.form.get('no_telefon', '').strip()

        # Validation
        if not nama_penuh or not no_id or not no_telefon:
            error = "Sila isi semua maklumat."
        elif len(nama_penuh) < 3:
            error = "Nama penuh tidak sah."
        elif not re.match(r'^[A-Z]{2}\d{6}$', no_id) and not re.match(r'^\d{5}$', no_id):
            error = "Format No. ID tidak sah. Pelajar: AB123456, Staf: 01234"
        elif not re.match(r'^01\d{8,9}$', no_telefon):
            error = "Format No. Telefon tidak sah. Contoh: 0123456789"
        else:
            # Valid - update and unlock
            conn.execute("""
                UPDATE sessions
                SET status = 'UNLOCKED',
                    nama_penuh = ?,
                    no_id = ?,
                    no_telefon = ?,
                    unlock_time = CURRENT_TIMESTAMP
                WHERE session_uuid = ?
            """, (nama_penuh, no_id, no_telefon, uuid))
            conn.commit()
            message = "PC Berjaya Dibuka! Anda boleh menutup browser ini."
            print(f"[UNLOCK] {nama_penuh} ({no_id}) - {uuid[:8]}...")

    # Fetch info — renamed to pc_row to avoid shadowing Flask session
    pc_row = conn.execute("SELECT pc_hostname, status, nama_penuh FROM sessions WHERE session_uuid = ?",
                          (uuid,)).fetchone()
    conn.close()

    if not pc_row:
        return "Sesi tidak ditemui atau tamat tempoh.", 404

    # HTML Template
    html = '''
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Unlock Lab PC</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a3a6e 0%, #2d5a9e 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 10px; }
            .card { background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); text-align: center; max-width: 400px; width: 100%; }
            h1 { color: #1a3a6e; margin-bottom: 5px; font-size: 1.4rem; }
            .subtitle { color: #666; font-size: 0.85rem; margin-bottom: 15px; }
            .pc-name { font-size: 1rem; background: #e8f4f8; padding: 10px; border-radius: 8px; margin: 15px 0; color: #1a3a6e; font-weight: bold; }
            .form-group { margin-bottom: 12px; text-align: left; }
            .form-group label { display: block; margin-bottom: 4px; font-weight: 600; color: #333; font-size: 0.9rem; }
            .form-group input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem; transition: border-color 0.3s; }
            .form-group input:focus { outline: none; border-color: #1a3a6e; }
            .form-group small { color: #888; font-size: 0.75rem; }
            .btn { background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); color: white; border: none; padding: 14px 30px; font-size: 1rem; border-radius: 8px; cursor: pointer; width: 100%; transition: transform 0.2s, box-shadow 0.2s; font-weight: bold; margin-top: 10px; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(243,156,18,0.4); }
            .btn:active { transform: translateY(0); }
            .success { color: #27ae60; font-weight: bold; padding: 20px; font-size: 1.1rem; }
            .error { color: #e74c3c; background: #fdeaea; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem; }
            .time-info { color: #666; font-size: 0.85rem; margin-top: 15px; }
            .footer { margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; color: #999; font-size: 0.75rem; }
        </style>
    </head>
    <body>
        <div class="card">
            <img src="/static/logo.png" alt="LabSentinel" style="width: 120px; height: 120px; margin-bottom: 10px;">
            <h1>Sistem Lab Sentinel</h1>
            <p class="subtitle">Sila isi maklumat untuk menggunakan komputer</p>

            {% if message %}
                <div class="success">{{ message }}</div>
                <div class="time-info">Had masa penggunaan: <strong>3 jam</strong></div>
                <div class="footer">Terima kasih kerana menggunakan makmal dengan bertanggungjawab.</div>
            {% elif pc.status == 'UNLOCKED' %}
                <div class="success">PC ini telah dibuka oleh {{ pc.nama_penuh or 'pengguna lain' }}.</div>
            {% else %}
                <div class="pc-name">{{ pc.pc_hostname }}</div>

                {% if error %}
                <div class="error">{{ error }}</div>
                {% endif %}

                <form method="POST">
                    <div class="form-group">
                        <label>Nama Penuh</label>
                        <input type="text" name="nama_penuh" placeholder="Contoh: Ahmad bin Abu" required>
                    </div>

                    <div class="form-group">
                        <label>No. Pelajar / Staf</label>
                        <input type="text" name="no_id" placeholder="Contoh: AB123456 atau 01234" required>
                        <small>Pelajar: AB123456 | Staf: 01234</small>
                    </div>

                    <div class="form-group">
                        <label>No. Telefon</label>
                        <input type="tel" name="no_telefon" placeholder="Contoh: 0123456789" required>
                    </div>

                    <button type="submit" class="btn">Buka Komputer</button>
                </form>

                <div class="time-info">Sesi akan tamat selepas 3 jam</div>
            {% endif %}

            <div class="footer">Powered by LabSentinel | HelmiSoftTech</div>
        </div>
    </body>
    </html>
    '''

    return render_template_string(html, message=message, error=error, pc=dict(pc_row))

@app.route('/test.php')
@app.route('/test')
@app.route('/lab-system/test.php')
@app.route('/lab-system/test')
def test():
    """Test endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'LabSentinel Server is running',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# ==================== AUTH ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
@app.route('/lab-system/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Login page untuk admin"""
    error = ''

    # Jika sudah login, redirect ke dashboard
    if get_current_admin():
        return redirect('/admin')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = 'Sila isi username dan password.'
        else:
            conn = get_db()
            user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                session['admin_id'] = user['id']
                session['admin_username'] = user['username']
                session['is_superadmin'] = bool(user['is_superadmin'])
                session['assigned_labs'] = user['assigned_labs'] or ''
                print(f"[AUTH] Login: {username}")
                return redirect('/admin')
            else:
                error = 'Username atau password tidak sah.'

    html = '''
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Login - LabSentinel</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a3a6e 0%, #2d5a9e 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 10px; }
            .card { background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); text-align: center; max-width: 400px; width: 100%; }
            h1 { color: #1a3a6e; margin-bottom: 5px; font-size: 1.4rem; }
            .subtitle { color: #666; font-size: 0.85rem; margin-bottom: 20px; }
            .form-group { margin-bottom: 15px; text-align: left; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 0.9rem; }
            .form-group input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem; transition: border-color 0.3s; }
            .form-group input:focus { outline: none; border-color: #1a3a6e; }
            .btn { background: linear-gradient(135deg, #1a3a6e 0%, #2d5a9e 100%); color: white; border: none; padding: 14px 30px; font-size: 1rem; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; transition: opacity 0.2s; }
            .btn:hover { opacity: 0.9; }
            .error { color: #e74c3c; background: #fdeaea; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem; }
            .footer { margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; color: #999; font-size: 0.75rem; }
        </style>
    </head>
    <body>
        <div class="card">
            <img src="/static/logo.png" alt="LabSentinel" style="width: 120px; height: 120px; margin-bottom: 10px;">
            <h1>LabSentinel Admin</h1>
            <p class="subtitle">Sila log masuk untuk akses dashboard</p>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
            <form method="POST">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" required autofocus>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn">Log Masuk</button>
            </form>
            <div class="footer">Powered by LabSentinel | HelmiSoftTech</div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, error=error)

@app.route('/admin/logout')
@app.route('/lab-system/admin/logout')
def admin_logout():
    """Logout admin"""
    username = session.get('admin_username', '?')
    session.clear()
    print(f"[AUTH] Logout: {username}")
    return redirect('/admin/login')

# ==================== ADMIN DASHBOARD ====================

@app.route('/admin')
@app.route('/lab-system/admin')
def admin():
    """Admin page - dashboard PC mengikut makmal + log pengguna"""
    # Auth check
    admin_user = get_current_admin()
    if not admin_user:
        return redirect('/admin/login')

    admin_labs = get_admin_labs(admin_user)

    selected_lab = request.args.get('lab', '')
    view = request.args.get('view', 'dashboard')

    conn = get_db()

    # Dapatkan senarai makmal unik untuk dropdown
    labs = conn.execute("""
        SELECT DISTINCT lab_name FROM sessions
        WHERE lab_name IS NOT NULL AND lab_name != ''
        ORDER BY lab_name
    """).fetchall()
    lab_list = [r['lab_name'] for r in labs]

    # Filter lab list for non-superadmin
    if admin_labs is not None:
        lab_list = [l for l in lab_list if l in admin_labs]

    # Dapatkan status terkini setiap PC (sesi paling baru per PC per makmal)
    pc_status = conn.execute("""
        SELECT s.session_uuid, s.pc_hostname, s.lab_name, s.status, s.nama_penuh, s.no_id, s.no_telefon,
               s.ip_address, s.mac_address, s.unlock_time, s.created_at, s.last_seen
        FROM sessions s
        INNER JOIN (
            SELECT pc_hostname, lab_name, MAX(id) as max_id
            FROM sessions
            WHERE lab_name IS NOT NULL AND lab_name != ''
            GROUP BY pc_hostname, lab_name
        ) latest ON s.id = latest.max_id
        ORDER BY s.lab_name, s.pc_hostname
    """).fetchall()

    # Kira is_online untuk setiap PC (last_seen < 2 minit lalu = online)
    now = datetime.utcnow()
    online_threshold = timedelta(minutes=2)
    pc_list = []
    for pc in pc_status:
        pc_dict = dict(pc)
        if pc_dict.get('last_seen'):
            try:
                last_seen_dt = datetime.strptime(pc_dict['last_seen'], '%Y-%m-%d %H:%M:%S')
                pc_dict['is_online'] = (now - last_seen_dt) < online_threshold
            except (ValueError, TypeError):
                pc_dict['is_online'] = False
        else:
            pc_dict['is_online'] = False
        pc_list.append(pc_dict)

    # Susun data mengikut makmal
    lab_pcs = {}
    for pc in pc_list:
        lab = pc['lab_name']
        if lab not in lab_pcs:
            lab_pcs[lab] = []
        lab_pcs[lab].append(pc)

    # Filter lab_pcs for non-superadmin
    if admin_labs is not None:
        lab_pcs = {k: v for k, v in lab_pcs.items() if k in admin_labs}

    # Validate selected_lab access
    if selected_lab and admin_labs is not None and selected_lab not in admin_labs:
        selected_lab = ''

    # Query log rekod dengan filter
    if selected_lab:
        records = conn.execute("""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL AND lab_name = ?
            ORDER BY id DESC
            LIMIT 100
        """, (selected_lab,)).fetchall()
    elif admin_labs is not None and admin_labs:
        # Non-superadmin: only show assigned labs
        placeholders = ','.join(['?' for _ in admin_labs])
        records = conn.execute(f"""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL AND lab_name IN ({placeholders})
            ORDER BY id DESC
            LIMIT 100
        """, admin_labs).fetchall()
    elif admin_labs is not None:
        # Non-superadmin with no labs assigned
        records = []
    else:
        # Superadmin: show all
        records = conn.execute("""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()
    conn.close()

    html = '''
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="60">
        <title>Admin - LabSentinel Dashboard</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { color: #1a3a6e; margin-bottom: 5px; }
            .subtitle { color: #666; margin-bottom: 20px; font-size: 0.9rem; }

            /* Admin Bar */
            .admin-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 12px 20px; background: white; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .admin-bar .user-info { color: #555; font-size: 0.9rem; }
            .admin-bar .user-info strong { color: #1a3a6e; }
            .admin-bar .badge-super { background: #f59e0b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-left: 5px; }
            .admin-bar .badge-admin { background: #3498db; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-left: 5px; }
            .admin-bar .badge-lab { background: #e8f4f8; color: #1a3a6e; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-left: 3px; }
            .admin-bar .bar-actions { display: flex; gap: 10px; align-items: center; }

            /* Tabs */
            .tabs { display: flex; gap: 0; margin-bottom: 20px; }
            .tab { padding: 12px 24px; background: #ddd; color: #555; text-decoration: none; font-weight: 600; font-size: 0.95rem; border: none; cursor: pointer; }
            .tab:first-child { border-radius: 8px 0 0 8px; }
            .tab:last-child { border-radius: 0 8px 8px 0; }
            .tab.active { background: #1a3a6e; color: white; }
            .tab:hover:not(.active) { background: #ccc; }

            /* Toolbar */
            .toolbar { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
            .stat-card { background: white; padding: 12px 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
            .stat-card h3 { margin: 0; color: #666; font-size: 0.8rem; }
            .stat-card .number { font-size: 1.8rem; color: #1a3a6e; font-weight: bold; }
            .filter-group { background: white; padding: 10px 16px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 8px; }
            .filter-group label { font-weight: 600; color: #333; font-size: 0.85rem; }
            .filter-group select { padding: 6px 10px; border: 2px solid #ddd; border-radius: 5px; font-size: 0.85rem; cursor: pointer; }
            .btn { color: white; padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; font-size: 0.85rem; text-decoration: none; display: inline-block; }
            .btn-green { background: #27ae60; }
            .btn-green:hover { background: #219a52; }
            .btn-blue { background: #3498db; }
            .btn-blue:hover { background: #2980b9; }
            .btn-red { background: #ef4444; }
            .btn-red:hover { background: #dc2626; }

            /* Dashboard - Lab Section */
            .lab-section { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 25px; overflow: hidden; }
            .lab-header { background: linear-gradient(135deg, #1a3a6e 0%, #2d5a9e 100%); color: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; }
            .lab-header h2 { margin: 0; font-size: 1.2rem; }
            .lab-header .lab-stats { display: flex; gap: 15px; font-size: 0.85rem; }
            .lab-header .lab-stats span { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 4px; }
            .pc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; padding: 20px; }
            .pc-card { border: 2px solid #eee; border-radius: 10px; padding: 12px; text-align: center; transition: transform 0.2s, box-shadow 0.2s; }
            .pc-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .pc-card.offline { border-color: #9ca3af; background: #f3f4f6; opacity: 0.7; }
            .pc-card.online-locked { border-color: #eab308; background: #fefce8; }
            .pc-card.online-unlocked { border-color: #27ae60; background: #f0fdf4; }
            .pc-card .pc-name { font-size: 1rem; font-weight: 700; color: #1a3a6e; margin-bottom: 6px; }
            .pc-card .pc-status { font-size: 0.75rem; font-weight: 600; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-bottom: 6px; }
            .pc-card .pc-status.offline { background: #e5e7eb; color: #6b7280; }
            .pc-card .pc-status.online-locked { background: #fef9c3; color: #a16207; }
            .pc-card .pc-status.online-unlocked { background: #dcfce7; color: #16a34a; }
            .pc-card .pc-user { font-size: 0.8rem; color: #555; }
            .pc-card .pc-id { font-size: 0.75rem; color: #888; }
            .pc-card .pc-time { font-size: 0.7rem; color: #aaa; margin-top: 4px; }

            /* Log Table */
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 0.85rem; }
            th { background: #1a3a6e; color: white; font-weight: 600; }
            tr:hover { background: #f8f9fa; }
            .status-unlocked { color: #27ae60; font-weight: bold; }
            .status-locked { color: #e74c3c; font-weight: bold; }
            .lab-badge { background: #e8f4f8; color: #1a3a6e; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }

            /* Command Buttons */
            .cmd-btns { margin-top: 8px; display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; }
            .cmd-btn { padding: 4px 10px; border: none; border-radius: 4px; font-size: 0.7rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }
            .cmd-btn:hover { opacity: 0.85; }
            .cmd-btn.lock { background: #eab308; color: #fff; }
            .cmd-btn.unlock { background: #22c55e; color: #fff; }
            .cmd-btn.restart { background: #f59e0b; color: #fff; }
            .cmd-btn.shutdown { background: #ef4444; color: #fff; }

            /* Toast Notification */
            .toast { position: fixed; top: 20px; right: 20px; padding: 14px 24px; border-radius: 8px; color: white; font-weight: 600; font-size: 0.9rem; z-index: 9999; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
            .toast.show { opacity: 1; }
            .toast.success { background: #16a34a; }
            .toast.error { background: #dc2626; }

            @media (max-width: 768px) {
                .pc-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
                table { font-size: 0.8rem; }
                th, td { padding: 6px; }
                .admin-bar { flex-direction: column; gap: 10px; text-align: center; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Admin Bar -->
            <div class="admin-bar">
                <span class="user-info">
                    Log masuk sebagai: <strong>{{ admin_user.username }}</strong>
                    {% if admin_user.is_superadmin %}
                        <span class="badge-super">Superadmin</span>
                    {% else %}
                        <span class="badge-admin">Pentadbir Makmal</span>
                        {% if admin_user.assigned_labs %}
                            {% for lab in admin_user.assigned_labs.split(',') %}
                                <span class="badge-lab">{{ lab.strip() }}</span>
                            {% endfor %}
                        {% endif %}
                    {% endif %}
                </span>
                <div class="bar-actions">
                    {% if admin_user.is_superadmin %}
                    <a href="/admin/users" class="btn btn-blue">Urus Admin</a>
                    {% endif %}
                    <a href="/admin/logout" class="btn btn-red">Logout</a>
                </div>
            </div>

            <div style="display: flex; align-items: center; gap: 12px;">
                <img src="/static/logo.png" alt="LabSentinel" style="width: 60px; height: 60px;">
                <div>
                    <h1 style="margin: 0;">LabSentinel Admin</h1>
                    {% if admin_user.is_superadmin %}
                    <p class="subtitle" style="margin: 0;">Sistem Pemantauan Makmal Komputer — Semua Makmal</p>
                    {% else %}
                    <p class="subtitle" style="margin: 0;">Sistem Pemantauan Makmal Komputer — Makmal Seliaan Anda</p>
                    {% endif %}
                </div>
            </div>

            <!-- Tabs -->
            <div class="tabs">
                <a href="/admin?view=dashboard" class="tab {{ 'active' if view == 'dashboard' else '' }}">Dashboard PC</a>
                <a href="/admin?view=log" class="tab {{ 'active' if view == 'log' else '' }}">Log Pengguna</a>
            </div>

            {% if view == 'dashboard' %}
            <!-- ==================== DASHBOARD VIEW ==================== -->

            <div class="toolbar">
                {% set total_pcs = lab_pcs.values()|map('length')|sum %}
                {% set online_pcs = [] %}
                {% set unlocked_pcs = [] %}
                {% for lab, pcs in lab_pcs.items() %}
                    {% for pc in pcs %}
                        {% if pc.is_online %}
                            {% if online_pcs.append(1) %}{% endif %}
                        {% endif %}
                        {% if pc.status == 'UNLOCKED' and pc.is_online %}
                            {% if unlocked_pcs.append(1) %}{% endif %}
                        {% endif %}
                    {% endfor %}
                {% endfor %}
                <div class="stat-card">
                    <h3>Jumlah Makmal</h3>
                    <div class="number">{{ lab_pcs|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>Jumlah PC</h3>
                    <div class="number">{{ total_pcs }}</div>
                </div>
                <div class="stat-card">
                    <h3>Online</h3>
                    <div class="number" style="color: #27ae60;">{{ online_pcs|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>Offline</h3>
                    <div class="number" style="color: #9ca3af;">{{ total_pcs - online_pcs|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>Sedang Digunakan</h3>
                    <div class="number" style="color: #eab308;">{{ unlocked_pcs|length }}</div>
                </div>
                <a href="/admin?view=dashboard" class="btn btn-blue">Refresh</a>
            </div>

            {% if lab_pcs %}
                {% for lab_name, pcs in lab_pcs.items() %}
                {% set lab_online = pcs|selectattr('is_online')|list|length %}
                {% set lab_aktif = pcs|selectattr('is_online')|selectattr('status', 'equalto', 'UNLOCKED')|list|length %}
                {% set lab_offline = pcs|length - lab_online %}
                <div class="lab-section">
                    <div class="lab-header">
                        <h2>{{ lab_name }}</h2>
                        <div class="lab-stats">
                            <span>{{ lab_online }} Online</span>
                            <span>{{ lab_aktif }} Aktif</span>
                            <span>{{ lab_offline }} Offline</span>
                        </div>
                    </div>
                    <div class="pc-grid">
                        {% for pc in pcs %}
                        {% if not pc.is_online %}
                        <div class="pc-card offline">
                            <div class="pc-name">{{ pc.pc_hostname }}</div>
                            <div class="pc-status offline">OFFLINE</div>
                            <div class="pc-user" style="color: #aaa;">-</div>
                        </div>
                        {% elif pc.status == 'UNLOCKED' %}
                        <div class="pc-card online-unlocked">
                            <div class="pc-name">{{ pc.pc_hostname }}</div>
                            <div class="pc-status online-unlocked">ONLINE · UNLOCKED</div>
                            {% if pc.nama_penuh %}
                            <div class="pc-user">{{ pc.nama_penuh }}</div>
                            <div class="pc-id">{{ pc.no_id or '' }}</div>
                            {% endif %}
                            {% if pc.unlock_time %}
                            <div class="pc-time">{{ pc.unlock_time }}</div>
                            {% endif %}
                            <div class="cmd-btns">
                                <button class="cmd-btn lock" onclick="sendCommand('{{ pc.session_uuid }}', 'LOCK', '{{ pc.pc_hostname }}')">Lock</button>
                                <button class="cmd-btn restart" onclick="sendCommand('{{ pc.session_uuid }}', 'RESTART', '{{ pc.pc_hostname }}')">Restart</button>
                                <button class="cmd-btn shutdown" onclick="sendCommand('{{ pc.session_uuid }}', 'SHUTDOWN', '{{ pc.pc_hostname }}')">Shutdown</button>
                            </div>
                        </div>
                        {% else %}
                        <div class="pc-card online-locked">
                            <div class="pc-name">{{ pc.pc_hostname }}</div>
                            <div class="pc-status online-locked">ONLINE · LOCKED</div>
                            <div class="pc-user" style="color: #aaa;">Menunggu pengguna</div>
                            <div class="cmd-btns">
                                <button class="cmd-btn unlock" onclick="sendCommand('{{ pc.session_uuid }}', 'UNLOCK', '{{ pc.pc_hostname }}')">Unlock</button>
                                <button class="cmd-btn restart" onclick="sendCommand('{{ pc.session_uuid }}', 'RESTART', '{{ pc.pc_hostname }}')">Restart</button>
                                <button class="cmd-btn shutdown" onclick="sendCommand('{{ pc.session_uuid }}', 'SHUTDOWN', '{{ pc.pc_hostname }}')">Shutdown</button>
                            </div>
                        </div>
                        {% endif %}
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div style="background: white; padding: 40px; border-radius: 12px; text-align: center; color: #888;">
                    {% if not admin_user.is_superadmin and not admin_user.assigned_labs %}
                    <p style="font-size: 1.2rem;">Tiada makmal ditugaskan kepada anda. Sila hubungi Superadmin untuk tetapkan makmal seliaan.</p>
                    {% else %}
                    <p style="font-size: 1.2rem;">Tiada data makmal. Jalankan client pada PC makmal untuk mula merekod.</p>
                    {% endif %}
                </div>
            {% endif %}

            {% else %}
            <!-- ==================== LOG VIEW ==================== -->

            <div class="toolbar">
                <div class="stat-card">
                    <h3>Jumlah Rekod</h3>
                    <div class="number">{{ records|length }}</div>
                </div>

                <div class="filter-group">
                    <label>Makmal:</label>
                    <select onchange="window.location.href='/admin?view=log' + (this.value ? '&lab=' + encodeURIComponent(this.value) : '')">
                        <option value="">Semua Makmal</option>
                        {% for lab in lab_list %}
                        <option value="{{ lab }}" {{ 'selected' if lab == selected_lab else '' }}>{{ lab }}</option>
                        {% endfor %}
                    </select>
                </div>

                <a href="/admin/export{{ '?lab=' + selected_lab if selected_lab else '' }}" class="btn btn-green">Export CSV</a>
                <a href="/admin?view=log{{ '&lab=' + selected_lab if selected_lab else '' }}" class="btn btn-blue">Refresh</a>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Makmal</th>
                        <th>PC</th>
                        <th>Nama Penuh</th>
                        <th>No. ID</th>
                        <th>No. Telefon</th>
                        <th>IP Address</th>
                        <th>MAC Address</th>
                        <th>Status</th>
                        <th>Masa Unlock</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in records %}
                    <tr>
                        <td>{{ r.id }}</td>
                        <td><span class="lab-badge">{{ r.lab_name or '-' }}</span></td>
                        <td>{{ r.pc_hostname }}</td>
                        <td>{{ r.nama_penuh }}</td>
                        <td>{{ r.no_id }}</td>
                        <td>{{ r.no_telefon }}</td>
                        <td>{{ r.ip_address or '-' }}</td>
                        <td><code>{{ r.mac_address or '-' }}</code></td>
                        <td class="status-{{ r.status|lower }}">{{ r.status }}</td>
                        <td>{{ r.unlock_time or '-' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}

            <div id="toast" class="toast"></div>

            <script>
            function showToast(msg, type) {
                var t = document.getElementById('toast');
                t.textContent = msg;
                t.className = 'toast ' + type + ' show';
                setTimeout(function() { t.className = 'toast'; }, 3000);
            }

            function sendCommand(uuid, command, pcName) {
                var labels = {SHUTDOWN: 'SHUTDOWN', LOCK: 'LOCK', UNLOCK: 'UNLOCK', RESTART: 'RESTART'};
                if (!confirm('AMARAN: ' + (labels[command] || command) + ' ' + pcName + '?')) return;

                var form = new FormData();
                form.append('uuid', uuid);
                form.append('command', command);

                fetch('/api.php?action=admin_command', {method: 'POST', body: form})
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.status === 'ok') {
                            showToast(command + ' dihantar ke ' + pcName, 'success');
                            setTimeout(function() { location.reload(); }, 1500);
                        } else {
                            showToast('Gagal: ' + (data.error || 'Unknown error'), 'error');
                        }
                    })
                    .catch(function(e) { showToast('Ralat rangkaian: ' + e, 'error'); });
            }
            </script>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, records=[dict(r) for r in records], lab_list=lab_list, selected_lab=selected_lab, lab_pcs=lab_pcs, view=view, admin_user=admin_user)

# ==================== ADMIN EXPORT ====================

@app.route('/admin/export')
@app.route('/lab-system/admin/export')
def admin_export():
    """Export rekod ke CSV (dengan filter makmal + lab isolation)"""
    # Auth check
    admin_user = get_current_admin()
    if not admin_user:
        return redirect('/admin/login')

    admin_labs = get_admin_labs(admin_user)
    selected_lab = request.args.get('lab', '')

    # Validate selected_lab access
    if selected_lab and admin_labs is not None and selected_lab not in admin_labs:
        selected_lab = ''

    conn = get_db()
    if selected_lab:
        records = conn.execute("""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL AND lab_name = ?
            ORDER BY id DESC
        """, (selected_lab,)).fetchall()
    elif admin_labs is not None and admin_labs:
        placeholders = ','.join(['?' for _ in admin_labs])
        records = conn.execute(f"""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL AND lab_name IN ({placeholders})
            ORDER BY id DESC
        """, admin_labs).fetchall()
    elif admin_labs is not None:
        records = []
    else:
        records = conn.execute("""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL
            ORDER BY id DESC
        """).fetchall()
    conn.close()

    # Generate CSV
    csv_content = "ID,Makmal,PC,Nama Penuh,No ID,No Telefon,IP Address,MAC Address,Status,Masa Unlock,Masa Daftar\n"
    for r in records:
        csv_content += f"{r['id']},{r['lab_name'] or ''},{r['pc_hostname']},{r['nama_penuh']},{r['no_id']},{r['no_telefon']},{r['ip_address'] or ''},{r['mac_address'] or ''},{r['status']},{r['unlock_time'] or ''},{r['created_at']}\n"

    filename = f"rekod_{selected_lab.replace(' ', '_')}.csv" if selected_lab else "rekod_semua_makmal.csv"
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

# ==================== ADMIN USER MANAGEMENT ====================

@app.route('/admin/users', methods=['GET', 'POST'])
@app.route('/lab-system/admin/users', methods=['GET', 'POST'])
def admin_users():
    """Halaman urus akaun pentadbir — superadmin sahaja"""
    admin_user = get_current_admin()
    if not admin_user:
        return redirect('/admin/login')
    if not admin_user['is_superadmin']:
        return redirect('/admin')

    msg = request.args.get('msg', '')
    error = ''

    conn = get_db()

    # Handle POST actions
    if request.method == 'POST':
        form_action = request.form.get('form_action', '')

        if form_action == 'add_admin':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            labs = request.form.getlist('labs')
            is_superadmin = 1 if request.form.get('is_superadmin') else 0
            assigned_labs = ','.join(labs)

            if not username or not password:
                error = 'Username dan password diperlukan.'
            elif len(password) < 3:
                error = 'Password terlalu pendek (minimum 3 aksara).'
            else:
                try:
                    conn.execute(
                        "INSERT INTO admin_users (username, password_hash, assigned_labs, is_superadmin) VALUES (?, ?, ?, ?)",
                        (username, generate_password_hash(password), assigned_labs, is_superadmin)
                    )
                    conn.commit()
                    conn.close()
                    print(f"[ADMIN] New admin created: {username} by {admin_user['username']}")
                    return redirect('/admin/users?msg=Admin+berjaya+ditambah')
                except sqlite3.IntegrityError:
                    error = f'Username "{username}" sudah wujud.'

        elif form_action == 'delete_admin':
            user_id = request.form.get('user_id', '')
            if user_id and int(user_id) != admin_user['id']:
                target = conn.execute("SELECT username FROM admin_users WHERE id = ?", (user_id,)).fetchone()
                conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                if target:
                    print(f"[ADMIN] Admin deleted: {target['username']} by {admin_user['username']}")
                return redirect('/admin/users?msg=Admin+berjaya+dipadam')
            else:
                error = 'Tidak boleh padam akaun sendiri.'

        elif form_action == 'change_password':
            user_id = request.form.get('user_id', '')
            new_password = request.form.get('new_password', '')
            if not new_password or len(new_password) < 3:
                error = 'Password baru terlalu pendek (minimum 3 aksara).'
            elif user_id:
                conn.execute(
                    "UPDATE admin_users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(new_password), user_id)
                )
                conn.commit()
                conn.close()
                print(f"[ADMIN] Password changed for user_id={user_id} by {admin_user['username']}")
                return redirect('/admin/users?msg=Password+berjaya+ditukar')

        elif form_action == 'edit_labs':
            user_id = request.form.get('user_id', '')
            labs = request.form.getlist('labs')
            assigned_labs = ','.join(labs)
            if user_id:
                conn.execute(
                    "UPDATE admin_users SET assigned_labs = ? WHERE id = ?",
                    (assigned_labs, user_id)
                )
                conn.commit()
                conn.close()
                print(f"[ADMIN] Labs updated for user_id={user_id} by {admin_user['username']}")
                return redirect('/admin/users?msg=Makmal+berjaya+dikemaskini')

        elif form_action == 'delete_lab':
            lab_name = request.form.get('lab_name', '').strip()
            if lab_name:
                # Padam semua sesi makmal ini
                conn.execute("DELETE FROM sessions WHERE lab_name = ?", (lab_name,))
                # Buang makmal dari assigned_labs setiap admin
                admins = conn.execute("SELECT id, assigned_labs FROM admin_users WHERE assigned_labs LIKE ?",
                                      (f'%{lab_name}%',)).fetchall()
                for adm in admins:
                    cleaned = [l.strip() for l in adm['assigned_labs'].split(',') if l.strip() and l.strip() != lab_name]
                    conn.execute("UPDATE admin_users SET assigned_labs = ? WHERE id = ?",
                                (','.join(cleaned), adm['id']))
                conn.commit()
                conn.close()
                print(f"[ADMIN] Lab deleted: {lab_name} by {admin_user['username']}")
                return redirect('/admin/users?msg=Makmal+berjaya+dibuang')
            else:
                error = 'Nama makmal diperlukan.'

    # Fetch all admin users
    if not conn._check_same_thread if hasattr(conn, '_check_same_thread') else False:
        conn = get_db()
    try:
        users = conn.execute("SELECT * FROM admin_users ORDER BY id").fetchall()
    except Exception:
        conn = get_db()
        users = conn.execute("SELECT * FROM admin_users ORDER BY id").fetchall()
    users = [dict(u) for u in users]

    # Fetch all available labs
    all_labs = conn.execute("""
        SELECT DISTINCT lab_name FROM sessions
        WHERE lab_name IS NOT NULL AND lab_name != ''
        ORDER BY lab_name
    """).fetchall()
    all_labs = [r['lab_name'] for r in all_labs]

    # Fetch lab stats untuk paparan Urus Makmal
    lab_stats = {}
    for lab in all_labs:
        pc_count = conn.execute("SELECT COUNT(DISTINCT pc_hostname) FROM sessions WHERE lab_name = ?", (lab,)).fetchone()[0]
        record_count = conn.execute("SELECT COUNT(*) FROM sessions WHERE lab_name = ? AND nama_penuh IS NOT NULL", (lab,)).fetchone()[0]
        lab_stats[lab] = {'pc_count': pc_count, 'record_count': record_count}

    conn.close()

    html = '''
    <!DOCTYPE html>
    <html lang="ms">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Urus Admin - LabSentinel</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
            .container { max-width: 1000px; margin: 0 auto; }
            h1 { color: #1a3a6e; margin-bottom: 5px; }
            .subtitle { color: #666; margin-bottom: 20px; font-size: 0.9rem; }

            /* Admin Bar */
            .admin-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 12px 20px; background: white; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .admin-bar .bar-actions { display: flex; gap: 10px; align-items: center; }

            /* Section */
            .section { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px; overflow: hidden; }
            .section-header { background: linear-gradient(135deg, #1a3a6e 0%, #2d5a9e 100%); color: white; padding: 15px 25px; }
            .section-header h2 { margin: 0; font-size: 1.1rem; }
            .section-body { padding: 20px; }

            /* Table */
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 0.85rem; }
            th { background: #f8f9fa; color: #333; font-weight: 600; }
            tr:hover { background: #f8f9fa; }

            /* Forms */
            .form-row { display: flex; gap: 15px; flex-wrap: wrap; }
            .form-group { margin-bottom: 15px; flex: 1; min-width: 200px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 0.85rem; }
            .form-group input, .form-group select { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 0.9rem; }
            .form-group input:focus, .form-group select:focus { outline: none; border-color: #1a3a6e; }
            .checkbox-group { display: flex; flex-wrap: wrap; gap: 10px; padding: 8px 0; }
            .checkbox-label { display: flex; align-items: center; gap: 5px; font-size: 0.85rem; color: #555; cursor: pointer; background: #f0f0f0; padding: 6px 12px; border-radius: 6px; }
            .checkbox-label:hover { background: #e0e0e0; }
            .checkbox-label input[type="checkbox"] { cursor: pointer; }

            /* Buttons */
            .btn { color: white; padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; font-size: 0.85rem; text-decoration: none; display: inline-block; font-weight: 600; }
            .btn-green { background: #27ae60; }
            .btn-green:hover { background: #219a52; }
            .btn-blue { background: #3498db; }
            .btn-blue:hover { background: #2980b9; }
            .btn-red { background: #ef4444; }
            .btn-red:hover { background: #dc2626; }
            .btn-small { padding: 5px 10px; font-size: 0.75rem; }

            /* Alerts */
            .alert { padding: 12px 20px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem; }
            .alert-success { background: #dcfce7; color: #16a34a; }
            .alert-error { background: #fdeaea; color: #e74c3c; }

            /* Badge */
            .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
            .badge-super { background: #f59e0b; color: white; }
            .badge-lab { background: #e8f4f8; color: #1a3a6e; margin: 2px; display: inline-block; }

            @media (max-width: 768px) {
                .form-row { flex-direction: column; }
                .form-group { min-width: 100%; }
                .admin-bar { flex-direction: column; gap: 10px; text-align: center; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Admin Bar -->
            <div class="admin-bar">
                <span style="color: #555; font-size: 0.9rem;">Urus Akaun Pentadbir</span>
                <div class="bar-actions">
                    <a href="/admin" class="btn btn-blue">Dashboard</a>
                    <a href="/admin/logout" class="btn btn-red">Logout</a>
                </div>
            </div>

            <div style="display: flex; align-items: center; gap: 12px;">
                <img src="/static/logo.png" alt="LabSentinel" style="width: 60px; height: 60px;">
                <div>
                    <h1 style="margin: 0;">Pengurusan Admin</h1>
                    <p class="subtitle" style="margin: 0;">Tambah, padam dan urus akaun pentadbir makmal</p>
                </div>
            </div>

            {% if msg %}
            <div class="alert alert-success">{{ msg }}</div>
            {% endif %}
            {% if error %}
            <div class="alert alert-error">{{ error }}</div>
            {% endif %}

            <!-- Senarai Admin -->
            <div class="section">
                <div class="section-header">
                    <h2>Senarai Pentadbir</h2>
                </div>
                <div class="section-body">
                    <table>
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Makmal Ditugaskan</th>
                                <th>Superadmin</th>
                                <th>Dicipta</th>
                                <th>Tindakan</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for u in users %}
                            <tr>
                                <td><strong>{{ u.username }}</strong></td>
                                <td>
                                    {% if u.is_superadmin %}
                                        <span class="badge badge-super">Semua Makmal</span>
                                    {% elif u.assigned_labs %}
                                        {% for lab in u.assigned_labs.split(',') %}
                                            <span class="badge badge-lab">{{ lab.strip() }}</span>
                                        {% endfor %}
                                    {% else %}
                                        <span style="color: #aaa;">Tiada</span>
                                    {% endif %}
                                </td>
                                <td>{{ 'Ya' if u.is_superadmin else 'Tidak' }}</td>
                                <td style="font-size: 0.8rem; color: #888;">{{ u.created_at }}</td>
                                <td>
                                    {% if u.id != current_admin_id %}
                                    <form method="POST" style="display:inline" onsubmit="return confirm('Padam admin {{ u.username }}?')">
                                        <input type="hidden" name="form_action" value="delete_admin">
                                        <input type="hidden" name="user_id" value="{{ u.id }}">
                                        <button type="submit" class="btn btn-red btn-small">Padam</button>
                                    </form>
                                    {% else %}
                                    <span style="color: #aaa; font-size: 0.8rem;">(Anda)</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Tambah Admin -->
            <div class="section">
                <div class="section-header">
                    <h2>Tambah Admin Baru</h2>
                </div>
                <div class="section-body">
                    <form method="POST">
                        <input type="hidden" name="form_action" value="add_admin">
                        <div class="form-row">
                            <div class="form-group">
                                <label>Username</label>
                                <input type="text" name="username" required placeholder="Contoh: guru_ali">
                            </div>
                            <div class="form-group">
                                <label>Password</label>
                                <input type="password" name="password" required placeholder="Minimum 3 aksara">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Makmal Ditugaskan</label>
                            {% if all_labs %}
                            <div class="checkbox-group">
                                {% for lab in all_labs %}
                                <label class="checkbox-label">
                                    <input type="checkbox" name="labs" value="{{ lab }}"> {{ lab }}
                                </label>
                                {% endfor %}
                            </div>
                            {% else %}
                            <p style="color: #aaa; font-size: 0.85rem;">Tiada makmal didaftarkan lagi. Jalankan client PC untuk mendaftar makmal.</p>
                            {% endif %}
                        </div>
                        <div class="form-group">
                            <label class="checkbox-label" style="background: #fef9c3;">
                                <input type="checkbox" name="is_superadmin" value="1"> Superadmin (akses semua makmal + urus admin)
                            </label>
                        </div>
                        <button type="submit" class="btn btn-green">Tambah Admin</button>
                    </form>
                </div>
            </div>

            <!-- Tukar Password -->
            <div class="section">
                <div class="section-header">
                    <h2>Tukar Password</h2>
                </div>
                <div class="section-body">
                    <form method="POST">
                        <input type="hidden" name="form_action" value="change_password">
                        <div class="form-row">
                            <div class="form-group">
                                <label>Pilih Admin</label>
                                <select name="user_id" required>
                                    {% for u in users %}
                                    <option value="{{ u.id }}">{{ u.username }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Password Baru</label>
                                <input type="password" name="new_password" required placeholder="Minimum 3 aksara">
                            </div>
                        </div>
                        <button type="submit" class="btn btn-blue">Tukar Password</button>
                    </form>
                </div>
            </div>

            <!-- Edit Makmal -->
            <div class="section">
                <div class="section-header">
                    <h2>Edit Makmal Ditugaskan</h2>
                </div>
                <div class="section-body">
                    <form method="POST">
                        <input type="hidden" name="form_action" value="edit_labs">
                        <div class="form-group">
                            <label>Pilih Admin</label>
                            <select name="user_id" id="edit-labs-select" onchange="updateLabCheckboxes()" required>
                                {% for u in users %}
                                <option value="{{ u.id }}" data-labs="{{ u.assigned_labs }}">{{ u.username }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Makmal Ditugaskan</label>
                            {% if all_labs %}
                            <div class="checkbox-group" id="edit-labs-checkboxes">
                                {% for lab in all_labs %}
                                <label class="checkbox-label">
                                    <input type="checkbox" name="labs" value="{{ lab }}"> {{ lab }}
                                </label>
                                {% endfor %}
                            </div>
                            {% else %}
                            <p style="color: #aaa; font-size: 0.85rem;">Tiada makmal didaftarkan lagi.</p>
                            {% endif %}
                        </div>
                        <button type="submit" class="btn btn-blue">Simpan Perubahan</button>
                    </form>
                </div>
            </div>

            <!-- Urus Makmal -->
            <div class="section">
                <div class="section-header" style="background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%);">
                    <h2>Urus Makmal</h2>
                </div>
                <div class="section-body">
                    {% if all_labs %}
                    <p style="color: #888; font-size: 0.85rem; margin-bottom: 15px;">Buang makmal akan <strong>memadam semua data sesi dan rekod pengguna</strong> makmal tersebut secara kekal.</p>
                    <table>
                        <thead>
                            <tr>
                                <th>Nama Makmal</th>
                                <th>Jumlah PC</th>
                                <th>Jumlah Rekod</th>
                                <th>Tindakan</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for lab in all_labs %}
                            <tr>
                                <td><strong>{{ lab }}</strong></td>
                                <td>{{ lab_stats[lab].pc_count }}</td>
                                <td>{{ lab_stats[lab].record_count }}</td>
                                <td>
                                    <form method="POST" style="display:inline" onsubmit="return confirm('AMARAN: Buang makmal \'{{ lab }}\'?\n\nSemua data ({{ lab_stats[lab].pc_count }} PC, {{ lab_stats[lab].record_count }} rekod) akan dipadam secara kekal.\n\nTindakan ini TIDAK boleh dibatalkan.')">
                                        <input type="hidden" name="form_action" value="delete_lab">
                                        <input type="hidden" name="lab_name" value="{{ lab }}">
                                        <button type="submit" class="btn btn-red btn-small">Buang</button>
                                    </form>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <p style="color: #aaa; font-size: 0.85rem;">Tiada makmal didaftarkan lagi.</p>
                    {% endif %}
                </div>
            </div>
        </div>

        <script>
        function updateLabCheckboxes() {
            var sel = document.getElementById('edit-labs-select');
            var labs = sel.options[sel.selectedIndex].getAttribute('data-labs') || '';
            var labArr = labs.split(',').map(function(l) { return l.trim(); });
            var checkboxes = document.querySelectorAll('#edit-labs-checkboxes input[type=checkbox]');
            checkboxes.forEach(function(cb) {
                cb.checked = labArr.indexOf(cb.value) !== -1;
            });
        }
        // Initialize on page load
        if (document.getElementById('edit-labs-select')) {
            updateLabCheckboxes();
        }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, users=users, all_labs=all_labs, lab_stats=lab_stats, current_admin_id=admin_user['id'], msg=msg, error=error)

# ==================== HOMEPAGE ====================

@app.route('/')
@app.route('/lab-system')
@app.route('/lab-system/')
def index():
    """Homepage"""
    return '''
    <html>
    <head><title>LabSentinel Server</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>LabSentinel Server</h1>
        <p>Server sedang berjalan.</p>
        <p><a href="/test">Test Connection</a></p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("=" * 50)
    print("   LABSENTINEL SERVER (Python Flask)")
    print("=" * 50)
    print(f"[INFO] Database: {DB_PATH}")
    print("[INFO] Starting server on http://0.0.0.0:5000")
    print("[INFO] Tekan Ctrl+C untuk berhenti")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=False)
