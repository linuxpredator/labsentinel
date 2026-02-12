# server.py - LabSentinel Python Backend
# Menggantikan PHP backend dengan Flask

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Database path
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
    for col in ['ip_address TEXT', 'mac_address TEXT', 'lab_name TEXT']:
        try:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {col}")
        except:
            pass
    conn.commit()
    conn.close()
    print("[DB] Database initialized")

# Initialize database on startup
init_db()

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
            conn.execute("INSERT INTO sessions (session_uuid, pc_hostname, ip_address, mac_address, lab_name) VALUES (?, ?, ?, ?, ?)",
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
        row = conn.execute("SELECT status FROM sessions WHERE session_uuid = ?",
                          (uuid,)).fetchone()
        conn.close()

        if row:
            return jsonify({'status': row['status']})
        else:
            return jsonify({'error': 'Session not found'})

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

    # Fetch info
    session = conn.execute("SELECT pc_hostname, status, nama_penuh FROM sessions WHERE session_uuid = ?",
                          (uuid,)).fetchone()
    conn.close()

    if not session:
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
            <h1>🖥️ Sistem Lab Sentinel</h1>
            <p class="subtitle">Sila isi maklumat untuk menggunakan komputer</p>

            {% if message %}
                <div class="success">✅ {{ message }}</div>
                <div class="time-info">⏱️ Had masa penggunaan: <strong>3 jam</strong></div>
                <div class="footer">Terima kasih kerana menggunakan makmal dengan bertanggungjawab.</div>
            {% elif session.status == 'UNLOCKED' %}
                <div class="success">✅ PC ini telah dibuka oleh {{ session.nama_penuh or 'pengguna lain' }}.</div>
            {% else %}
                <div class="pc-name">{{ session.pc_hostname }}</div>

                {% if error %}
                <div class="error">⚠️ {{ error }}</div>
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

                    <button type="submit" class="btn">🔓 Buka Komputer</button>
                </form>

                <div class="time-info">⏱️ Sesi akan tamat selepas 3 jam</div>
            {% endif %}

            <div class="footer">Powered by LabSentinel | HelmiSoftTech</div>
        </div>
    </body>
    </html>
    '''

    return render_template_string(html, message=message, error=error, session=dict(session))

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

@app.route('/admin')
@app.route('/lab-system/admin')
def admin():
    """Admin page - dashboard PC mengikut makmal + log pengguna"""
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

    # Dapatkan status terkini setiap PC (sesi paling baru per PC per makmal)
    pc_status = conn.execute("""
        SELECT s.pc_hostname, s.lab_name, s.status, s.nama_penuh, s.no_id, s.no_telefon,
               s.ip_address, s.mac_address, s.unlock_time, s.created_at
        FROM sessions s
        INNER JOIN (
            SELECT pc_hostname, lab_name, MAX(id) as max_id
            FROM sessions
            WHERE lab_name IS NOT NULL AND lab_name != ''
            GROUP BY pc_hostname, lab_name
        ) latest ON s.id = latest.max_id
        ORDER BY s.lab_name, s.pc_hostname
    """).fetchall()

    # Susun data mengikut makmal
    lab_pcs = {}
    for pc in pc_status:
        lab = pc['lab_name']
        if lab not in lab_pcs:
            lab_pcs[lab] = []
        lab_pcs[lab].append(dict(pc))

    # Query log rekod dengan filter
    if selected_lab:
        records = conn.execute("""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL AND lab_name = ?
            ORDER BY id DESC
            LIMIT 100
        """, (selected_lab,)).fetchall()
    else:
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
        <title>Admin - LabSentinel Dashboard</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { color: #1a3a6e; margin-bottom: 5px; }
            .subtitle { color: #666; margin-bottom: 20px; font-size: 0.9rem; }

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

            /* Dashboard - Lab Section */
            .lab-section { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 25px; overflow: hidden; }
            .lab-header { background: linear-gradient(135deg, #1a3a6e 0%, #2d5a9e 100%); color: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; }
            .lab-header h2 { margin: 0; font-size: 1.2rem; }
            .lab-header .lab-stats { display: flex; gap: 15px; font-size: 0.85rem; }
            .lab-header .lab-stats span { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 4px; }
            .pc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; padding: 20px; }
            .pc-card { border: 2px solid #eee; border-radius: 10px; padding: 12px; text-align: center; transition: transform 0.2s, box-shadow 0.2s; }
            .pc-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .pc-card.locked { border-color: #e74c3c; background: #fef2f2; }
            .pc-card.unlocked { border-color: #27ae60; background: #f0fdf4; }
            .pc-card .pc-name { font-size: 1rem; font-weight: 700; color: #1a3a6e; margin-bottom: 6px; }
            .pc-card .pc-status { font-size: 0.75rem; font-weight: 600; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-bottom: 6px; }
            .pc-card .pc-status.locked { background: #fee2e2; color: #dc2626; }
            .pc-card .pc-status.unlocked { background: #dcfce7; color: #16a34a; }
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

            @media (max-width: 768px) {
                .pc-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
                table { font-size: 0.8rem; }
                th, td { padding: 6px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LabSentinel Admin</h1>
            <p class="subtitle">Sistem Pemantauan Makmal Komputer</p>

            <!-- Tabs -->
            <div class="tabs">
                <a href="/admin?view=dashboard" class="tab {{ 'active' if view == 'dashboard' else '' }}">Dashboard PC</a>
                <a href="/admin?view=log" class="tab {{ 'active' if view == 'log' else '' }}">Log Pengguna</a>
            </div>

            {% if view == 'dashboard' %}
            <!-- ==================== DASHBOARD VIEW ==================== -->

            <div class="toolbar">
                {% set total_pcs = lab_pcs.values()|map('length')|sum %}
                {% set unlocked_pcs = [] %}
                {% for lab, pcs in lab_pcs.items() %}
                    {% for pc in pcs %}
                        {% if pc.status == 'UNLOCKED' %}
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
                    <h3>Sedang Digunakan</h3>
                    <div class="number" style="color: #27ae60;">{{ unlocked_pcs|length }}</div>
                </div>
                <div class="stat-card">
                    <h3>Tersedia</h3>
                    <div class="number" style="color: #3498db;">{{ total_pcs - unlocked_pcs|length }}</div>
                </div>
                <a href="/admin?view=dashboard" class="btn btn-blue">🔄 Refresh</a>
            </div>

            {% if lab_pcs %}
                {% for lab_name, pcs in lab_pcs.items() %}
                {% set unlocked_count = pcs|selectattr('status', 'equalto', 'UNLOCKED')|list|length %}
                <div class="lab-section">
                    <div class="lab-header">
                        <h2>{{ lab_name }}</h2>
                        <div class="lab-stats">
                            <span>{{ pcs|length }} PC</span>
                            <span>{{ unlocked_count }} Aktif</span>
                            <span>{{ pcs|length - unlocked_count }} Tersedia</span>
                        </div>
                    </div>
                    <div class="pc-grid">
                        {% for pc in pcs %}
                        <div class="pc-card {{ pc.status|lower }}">
                            <div class="pc-name">{{ pc.pc_hostname }}</div>
                            <div class="pc-status {{ pc.status|lower }}">{{ pc.status }}</div>
                            {% if pc.nama_penuh %}
                            <div class="pc-user">{{ pc.nama_penuh }}</div>
                            <div class="pc-id">{{ pc.no_id or '' }}</div>
                            {% else %}
                            <div class="pc-user" style="color: #aaa;">Tiada pengguna</div>
                            {% endif %}
                            {% if pc.unlock_time %}
                            <div class="pc-time">{{ pc.unlock_time }}</div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div style="background: white; padding: 40px; border-radius: 12px; text-align: center; color: #888;">
                    <p style="font-size: 1.2rem;">Tiada data makmal. Jalankan client pada PC makmal untuk mula merekod.</p>
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

                <a href="/admin/export{{ '?lab=' + selected_lab if selected_lab else '' }}" class="btn btn-green">📥 Export CSV</a>
                <a href="/admin?view=log{{ '&lab=' + selected_lab if selected_lab else '' }}" class="btn btn-blue">🔄 Refresh</a>
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
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, records=[dict(r) for r in records], lab_list=lab_list, selected_lab=selected_lab, lab_pcs=lab_pcs, view=view)

@app.route('/admin/export')
@app.route('/lab-system/admin/export')
def admin_export():
    """Export rekod ke CSV (dengan filter makmal)"""
    selected_lab = request.args.get('lab', '')

    conn = get_db()
    if selected_lab:
        records = conn.execute("""
            SELECT id, pc_hostname, lab_name, nama_penuh, no_id, no_telefon, ip_address, mac_address, status, unlock_time, created_at
            FROM sessions
            WHERE nama_penuh IS NOT NULL AND lab_name = ?
            ORDER BY id DESC
        """, (selected_lab,)).fetchall()
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

    from flask import Response
    filename = f"rekod_{selected_lab.replace(' ', '_')}.csv" if selected_lab else "rekod_semua_makmal.csv"
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/')
@app.route('/lab-system')
@app.route('/lab-system/')
def index():
    """Homepage"""
    return '''
    <html>
    <head><title>LabSentinel Server</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🖥️ LabSentinel Server</h1>
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
