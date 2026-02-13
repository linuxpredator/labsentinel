# LabSentinel Project Status
**Last Updated**: 2026-02-13 (Admin Auth System — Superadmin/Pentadbir Makmal + Server-Side Verification)

## Current Phase: TESTING & DEPLOYMENT

## System Status Overview
| Component | Status | Tested | Notes |
| :--- | :--- | :--- | :--- |
| **Client App** (`client.py`) | **Operational** | GUI PASS | Fullscreen lock screen, QR unlock, 3-jam session limit + clean unlock view + Matrix Digital Rain + logo.ico icon |
| **Server API** (`server.py`) | **Operational** | 16/16 PASS | Python Flask backend pada port 5000, multi-lab support |
| **Setup Wizard** (`setup_wizard.py`) | **Operational** | PASS | Installer penuh: install ke `C:\Program Files\LabSentinel`, daftar Installed Apps, uninstall dilindungi password |
| **Build System** (`build_app.bat`) | **Operational** | - | PyInstaller build script, menghasilkan .exe |
| **Remote Access - PythonAnywhere** | **Operational** | PASS | `https://labsentinel.xyz` — paid plan ($10/bulan), custom domain, Let's Encrypt SSL, sentiasa online |
| **Remote Access - Cloudflare** | **Deprecated** | - | Named Tunnel `labsentinel` → `lab.labsentinel.xyz` — diganti PythonAnywhere (masalah 503 bila captive portal IT) |
| **Admin Panel** (`/admin`) | **Operational** | PASS | **Dashboard PC** (grid visual per makmal) + **Log Pengguna** (jadual + filter + CSV export) + Remote commands (Shutdown/Restart/Lock/Unlock) |
| **Auth System** (`admin_users`) | **Operational** | PASS | Superadmin + Pentadbir Makmal, login session-based, password hashed (Werkzeug), lab isolation, `verify_admin` API untuk client |
| **Built Executables** (`dist/`) | **Up-to-date** | - | Rebuild 2026-02-13: Setup (19MB) + Client (23MB) — logo.ico bundled, URL `labsentinel.xyz`, server-side admin verify |
| **Deployment Package** (`deploy/`) | **Up-to-date** | - | Folder siap copy: EXE + config + logo + logo.ico + banner.png + INSTALL.txt |
| **Deploy Location** (`E:\Program\LabSentinel`) | **Copied** | - | Pakej lengkap disalin ke E:\Program untuk deploy manual ke PC makmal |
| **Database** (`lab_system.db`) | **Clean** | - | Test data dibuang — dashboard bermula kosong, data masuk mengikut PC yang register |

## Server Hosting — PythonAnywhere
| Item | Status | Detail |
| :--- | :--- | :--- |
| **PythonAnywhere Account** | **Active** | Username: `linuxpredator`, Paid plan ($10/bulan) |
| **Server URL** | **Live** | `https://labsentinel.xyz` (custom domain) |
| **Plan** | **Paid** | $10/bulan — custom domain, 5000s CPU, 3 workers, tiada expiry |
| **Python Version** | 3.9 | WSGI-based (tiada tunnel diperlukan) |
| **SSL** | **Active** | Let's Encrypt auto-renew (valid hingga May 2026) |
| **WSGI Config** | **Configured** | `/var/www/labsentinel_xyz_wsgi.py` → `from server import app` |
| **Source Directory** | **Set** | `/home/linuxpredator/labsentinel/` |
| **Database** | **Auto-created** | `~/labsentinel_data/lab_system.db` (writable directory) |
| **HTTPS** | **Enforced** | Force HTTPS enabled |
| **Expiry** | **Tiada** | Paid plan — tiada expiry, sentiasa aktif |

### Target Configuration (Selepas Setup Siap)
```json
{
    "lab_name": "General Lab",
    "pc_name": "PC-01",
    "admin_password": "<fallback offline sahaja>",
    "server_url": "https://labsentinel.xyz",
    "auto_start": true
}
```
> **Sentiasa online** — tiada bergantung pada tunnel atau login internet PC server.
> **Nota**: `admin_password` dalam config.json kini hanya digunakan sebagai fallback apabila server tidak boleh dicapai. Password utama disahkan melalui server (`admin_users` DB).

### Kenapa PythonAnywhere (bukan Cloudflare Tunnel)?
- **Masalah 503**: PC server perlukan login captive portal IT sebelum tunnel connect. Selagi tunnel down, pengguna scan QR → 503.
- **Penyelesaian**: Flask server di-host terus di cloud (PythonAnywhere free tier). Server sentiasa accessible dari phone pengguna.
- Cloudflare Tunnel (`lab.labsentinel.xyz`) masih boleh digunakan sebagai fallback jika diperlukan.

### Domain & Tunnel (Legacy/Fallback)
| Item | Status | Detail |
| :--- | :--- | :--- |
| **Domain** | **Purchased** | `labsentinel.xyz` via Shinjiru (RM6.90/tahun) |
| **Cloudflare Account** | **Created** | `Linuxpredator@gmail.com` |
| **Named Tunnel** | **Deprecated** | ID: `e3992090-b77d-4b30-a943-fb74d7742a6b`, route `lab.labsentinel.xyz` → Flask :5000 |

## Database Schema
```sql
sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid    TEXT UNIQUE NOT NULL,
    pc_hostname     TEXT NOT NULL,
    status          TEXT DEFAULT 'LOCKED',
    nama_penuh      TEXT,
    no_id           TEXT,
    no_telefon      TEXT,
    ip_address      TEXT,
    mac_address     TEXT,
    lab_name        TEXT,              -- Nama makmal untuk multi-lab filter
    unlock_time     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen       DATETIME,          -- Polling terakhir (online/offline detection)
    pending_command TEXT               -- Remote command: SHUTDOWN/RESTART/LOCK/UNLOCK
)

admin_users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,      -- Werkzeug hashed password
    assigned_labs   TEXT DEFAULT '',    -- CSV makmal ditugaskan (kosong = tiada akses)
    is_superadmin   INTEGER DEFAULT 0, -- 1 = akses semua makmal + urus admin
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
)
-- Default superadmin: admin/admin (dicipta automatik jika table kosong)
```

## Sistem Peranan Admin
| Peranan | Dashboard | Arahan PC | Urus Admin | Akses Makmal |
| :--- | :--- | :--- | :--- | :--- |
| **Superadmin** | Semua makmal | Shutdown/Restart/Lock/Unlock semua PC | Ya (tambah/padam/tukar password) | Semua |
| **Pentadbir Makmal** | Makmal seliaan sahaja | Shutdown/Restart/Lock/Unlock PC makmal sendiri | Tidak | Hanya makmal yang ditugaskan |

### Aliran Pengesahan Admin (Client → Server)
```
Client admin_unlock() → POST /api.php?action=verify_admin
                         { password, lab_name }
                              ↓
                    Server semak admin_users DB
                    (password hash + lab access)
                              ↓
                    { verified: true/false }
                              ↓
              ✓ → Unlock PC   |   ✗ → Password ditolak

              Server tidak boleh dicapai → Fallback password config.json (offline sahaja)
```

## File Inventory
| File | Type | Status | Description |
| :--- | :--- | :--- | :--- |
| `client.py` | Core | **Active** | Tkinter lock screen client + clean unlock view + admin buttons + Matrix Digital Rain |
| `server.py` | Core | **Active** | Flask API backend + admin panel (multi-lab filter) + unlock page |
| `setup_wizard.py` | Core | **Active** | GUI wizard — pemilik makmal taip nama makmal + nama PC |
| `config.json` | Config | **Active** | Runtime configuration |
| `lab_system.db` | Data | **Active** | SQLite database (sessions + IP/MAC + lab_name) |
| `build_app.bat` | Tool | **Active** | PyInstaller build script |
| `START_ALL.bat` | Tool | **Active** | Launcher (server + tunnel) |
| `start_server.bat` | Tool | **Active** | Flask server starter |
| `wsgi.py` | Config | **Active** | PythonAnywhere WSGI entry point |
| `start_cloudflare.bat` | Tool | **Deprecated** | Cloudflare tunnel starter (diganti PythonAnywhere) |
| `cloudflared.exe` | Binary | **Present** | Cloudflare tunnel executable (legacy) |
| `logo.png` | Asset | **Present** | App logo |
| `logo.ico` | Asset | **Present** | Windows icon (title bar + taskbar) |
| `banner.png` | Asset | **Present** | Setup wizard sidebar banner |
| `dist/` | Output | **Up-to-date** | Rebuild 2026-02-13: Setup (19MB) + Client (23MB) |
| `deploy/LabSentinel/` | Output | **Up-to-date** | Pakej deployment: EXE + config.json + logo.png + logo.ico + INSTALL.txt |

## End-to-End Test Results (2026-02-12, PythonAnywhere Deployment)
Ujian penuh client flow terhadap `https://labsentinel.xyz`

| # | Ujian | Keputusan |
| :--- | :--- | :--- |
| 1 | Register (`api.php?action=register`) | PASS — `{"status":"registered"}` |
| 2 | Poll status (`api.php?action=check`) | PASS — `{"status":"LOCKED"}` |
| 3 | Unlock page GET (`unlock.php?uuid=...`) | PASS — HTTP 200 |
| 4 | Unlock POST (form submit dengan data sah) | PASS — "PC Berjaya Dibuka" |
| 5 | Poll after unlock | PASS — `{"status":"UNLOCKED"}` |
| 6 | Admin panel (rekod pengguna) | PASS — data muncul dalam log |
| 7 | Phone scan QR (mobile data) | PASS — borang muncul, submit berjaya, "PC Berjaya Dibuka" |
| 8 | Server-side verify after phone unlock | PASS — `{"status":"UNLOCKED"}` |
| | **JUMLAH** | **8/8 PASS (100%)** |

## End-to-End Test Results (2026-02-11, Multi-Lab Test)
Ujian multi-makmal dijalankan melalui localhost

| # | Ujian | Keputusan |
| :--- | :--- | :--- |
| 1 | Register Lab Multimedia (LM-PC-01) | PASS — status registered |
| 2 | Register Lab Cyber Security (CS-PC-01) | PASS — status registered |
| 3 | Unlock Lab Multimedia | PASS — PC Berjaya Dibuka |
| 4 | Unlock Lab Cyber Security | PASS — PC Berjaya Dibuka |
| 5 | Admin Panel - Semua Makmal | PASS — kedua-dua makmal dipaparkan |
| 6 | Admin Panel - Filter Lab Multimedia | PASS — hanya data Multimedia |
| 7 | Admin Panel - Filter Lab Cyber Security | PASS — hanya data Cyber Security |
| | **JUMLAH** | **7/7 PASS (100%)** |

## Previous Test Results (2026-02-11, Post-Password Update)
Ujian penuh dijalankan melalui localhost + Named Tunnel `https://lab.labsentinel.xyz`

| # | Ujian | Keputusan |
| :--- | :--- | :--- |
| 1 | Health Check (localhost) | PASS — status ok, server running |
| 2 | Health Check (tunnel) | PASS — status ok via `lab.labsentinel.xyz` |
| 3 | Homepage | PASS — HTTP 200 |
| 4 | Register Session | PASS — status registered |
| 5 | Check Status (LOCKED) | PASS — status LOCKED |
| 6 | Unlock Page (GET) | PASS — HTTP 200 |
| 7 | Validation - Nama Kosong | PASS — rejects empty name |
| 8 | Validation - ID Tidak Sah | PASS — rejects bad ID format |
| 9 | Validation - Telefon Tidak Sah | PASS — rejects bad phone format |
| 10 | Unlock POST (Data Sah) | PASS — PC Berjaya Dibuka |
| 11 | Check Status (UNLOCKED) | PASS — status UNLOCKED |
| 12 | Admin Panel + IP/MAC | PASS — HTTP 200, data + MAC verified |
| 13 | CSV Export | PASS — HTTP 200, data verified |
| 14 | Tunnel - Register | PASS — status registered via tunnel |
| 15 | Tunnel - Check Status | PASS — status LOCKED via tunnel |
| 16 | Tunnel - Admin Panel | PASS — HTTP 200 via tunnel |
| | **JUMLAH** | **16/16 PASS (100%)** |

## Physical Testing Checklist
- [x] PC terkunci fullscreen (cursor hilang, Alt+Tab disekat)
- [x] Matrix Digital Rain effect dipaparkan pada latar belakang lock screen
- [x] QR Code boleh discan oleh telefon bimbit
- [x] Halaman unlock terbuka di browser (diuji via API + QR scan)
- [x] Borang validation menolak input tidak sah (3 kes diuji: nama kosong, ID salah, telefon salah)
- [x] Unlock berjaya selepas isi borang (diuji via API, status UNLOCKED disahkan)
- [x] Countdown timer berjalan di unlock view (window kecil 420x280)
- [ ] Auto-lock apabila masa tamat (QR baru dijana + matrix rain restart)
- [x] Admin unlock berfungsi (Ctrl+Alt+L / Escape / butang — password protected)
- [x] Unlock view bersih: hanya ACCESS GRANTED + countdown + butang Admin Panel & Settings
- [x] Admin Panel dilindungi password dari client app
- [x] Settings dilindungi password dari client app
- [x] Admin panel papar rekod pengguna dengan IP dan MAC address
- [x] Admin panel filter mengikut makmal (dropdown)
- [x] CSV export mengandungi kolum Makmal, IP dan MAC address
- [x] CSV export ikut filter makmal yang dipilih
- [x] Phone scan QR via mobile data → unlock berjaya (PythonAnywhere, tiada 503)
- [ ] Admin unlock sahkan password melalui server (bukan config.json)
- [ ] Pentadbir Makmal A tidak boleh nampak Makmal B di dashboard
- [ ] Pentadbir Makmal A tidak boleh SHUTDOWN/RESTART/LOCK/UNLOCK PC Makmal B
- [ ] Superadmin boleh nampak dan kawal semua makmal
- [ ] Multi-PC serentak berfungsi
- [x] Cloudflare Named Tunnel berfungsi dari rangkaian luar
- [x] Ikon LabSentinel pada title bar window
- [x] Ikon LabSentinel pada Installed Apps, Setup Wizard, dan uninstall dialog
- [x] Uninstall bunuh process client sebelum padam fail
- [ ] .exe (LabSentinel Client.exe) berfungsi tanpa Python

## Completed Milestones
- [x] **Backend Migration**: PHP ke Python Flask (tiada perlu XAMPP)
- [x] **Session Time Limit**: Had 3 jam untuk setiap sesi pengguna
- [x] **Countdown Timer**: Paparan countdown di unlock view (window kecil 420x280)
- [x] **Auto-lock**: PC kunci semula apabila masa tamat + UUID baru dijana
- [x] **Cloudflare Tunnel**: Tunnel utama (tiada warning page, percuma)
- [x] ~~**Dual Tunnel Support**~~: Ngrok dibuang -- Cloudflare sahaja
- [x] **Admin Panel**: Halaman `/admin` untuk lihat rekod pengguna + export CSV
- [x] **Multi-Lab Filter**: Dropdown filter mengikut makmal di admin panel + CSV export
- [x] **User Registration Form**: Borang unlock memerlukan Nama, No ID, No Telefon
- [x] **Input Validation**: Regex validation untuk No ID (pelajar/staf) dan No Telefon
- [x] **Offline Mode**: Butang unlock kecemasan apabila server tidak boleh dicapai (5 fail berturut-turut)
- [x] **Admin Override**: Ctrl+Alt+L / Escape / butang Admin untuk manual unlock (password protected)
- [x] **Clean Unlock View**: Selepas unlock, window kecil hanya papar ACCESS GRANTED + countdown + butang admin
- [x] **Password-Protected Admin Access**: Butang Admin Panel dan Settings memerlukan password
- [x] **Custom Window Icon**: Ikon LabSentinel pada title bar dan taskbar (AppUserModelID)
- [x] **EXE Build Pipeline**: `build_app.bat` menghasilkan standalone executables
- [x] **Setup Wizard**: GUI installer profesional dengan sidebar, validation, auto-start
- [x] **IP & MAC Logging**: Merekod IP address dan MAC address setiap sesi untuk audit keselamatan
- [x] **Matrix Digital Rain**: Animasi hujan aksara Jawi pada latar belakang lock screen
- [x] **Superadmin & Admin Roles**: Table `admin_users` dengan `is_superadmin` dan `assigned_labs`. Superadmin akses semua, admin biasa akses makmal seliaan sahaja.
- [x] **Admin Login System**: Session-based login (`/admin/login`), password hashed (Werkzeug), logout, redirect jika belum login
- [x] **Lab Isolation**: Dashboard, log, CSV export, dan remote commands dihadkan mengikut makmal yang ditugaskan kepada admin
- [x] **Remote PC Commands**: Shutdown, Restart, Lock, Unlock dari admin dashboard dengan popup amaran 30 saat (shutdown/restart)
- [x] **Admin User Management**: Superadmin boleh tambah/padam admin, tukar password, edit makmal ditugaskan (`/admin/users`)
- [x] **Server-Side Admin Verification**: Endpoint `verify_admin` — client sahkan password melalui server, bukan plaintext config. Fallback offline ke config.json.
- [x] **Rebranding**: 'Sistem Makmal KKP' -> 'Sistem Lab Sentinel', 'FKEKK' -> 'HelmiSoftTech'
- [x] **Transparent UI**: Layout `place()` supaya matrix rain nampak penuh di latar belakang
- [x] **Domain Purchased**: `labsentinel.xyz` dibeli via Shinjiru (RM6.90/tahun)
- [x] **Named Cloudflare Tunnel**: URL tetap `lab.labsentinel.xyz` (Tunnel ID: e3992090-b77d-4b30-a943-fb74d7742a6b)
- [x] **Deployment Package**: Folder `deploy/LabSentinel/` sedia untuk copy ke PC ujian
- [x] **PythonAnywhere Deployment**: Server di-host ke cloud (`labsentinel.xyz`) — sentiasa online, tiada bergantung pada tunnel/captive portal

## Architecture
```
                              INTERNET
                                 |
              [labsentinel.xyz]    <-- Sentiasa online (PythonAnywhere)
                                 |
                        [PythonAnywhere WSGI]
                                 |
                          [Flask Server]
                    /        |        |        \
             /api.php   /unlock.php  /admin   /admin/users
             (register,  (user form)  (dashboard,  (superadmin:
              check,                   log, CSV,    tambah/padam
              verify_admin,            remote cmd)  admin, tukar
              admin_command,                        password,
              lab_name)                             edit makmal)
                    |
               [SQLite DB]
               (~/labsentinel_data/lab_system.db)
              /            \
     [sessions]      [admin_users]
     (PC data,       (username,
      user info,      password_hash,
      lab_name)       assigned_labs,
                      is_superadmin)
                           |
          ┌────────────────┼────────────────┐
          │                │                │
    [Superadmin]    [Admin Makmal A]  [Admin Makmal B]
    (semua makmal)  (Lab A sahaja)    (Lab B sahaja)
          |                |                |
    ┌─────┴─────┐         |                |
    │           │         │                │
  [Lab A]    [Lab B]    [Lab A]          [Lab B]
  PC-01..N   PC-01..N   PC-01..N         PC-01..N
```

## Session Flow
```
PC Locked (QR displayed + Matrix Digital Rain background)
        |
        v
Client sends register(uuid, pc_name, lab_name, mac_address) --> Server saves IP + MAC + lab_name
        |
        v
User scans QR --> Opens unlock page (mobile browser)
        |
        v
User fills form (Nama, No ID, No Telefon) --> Validation
        |
        v
Data saved + Status = UNLOCKED
        |
        v
Client polls /api.php?action=check --> Detects UNLOCKED
        |
        v
Clean unlock view: ACCESS GRANTED + countdown + Admin Panel/Settings buttons
        |
        v
Time expires --> PC locks again (new UUID + QR generated + Matrix rain restarts)
```

## How to Run

### Local Testing (Satu PC)
1. Double-click `start_server.bat`
2. Double-click `client.py` atau `dist/LabSentinel Client.exe`

### Remote/Multi-PC Setup
1. Server sudah online di `https://labsentinel.xyz` (tiada perlu jalankan apa-apa)
2. Pastikan `config.json` pada setiap PC client ada `"server_url": "https://labsentinel.xyz"`
3. Set `"lab_name"` mengikut makmal (contoh: "Lab Multimedia", "Lab Cyber Security")
4. Jalankan client pada setiap PC

### Build Executables
1. Double-click `build_app.bat`
2. Output: `dist/LabSentinel Setup.exe` + `dist/LabSentinel Client.exe`

## Known Issues / Notes
- ~~Fail PHP deprecated~~ → Dipadam 2026-02-11
- ~~URL Cloudflare Tunnel berubah setiap kali dimulakan semula~~ → Diselesaikan dengan Named Tunnel (`lab.labsentinel.xyz`)
- ~~503 bila captive portal IT belum login~~ → Diselesaikan dengan PythonAnywhere (server di cloud, tiada tunnel)
- ~~Admin password disimpan dalam plaintext di `config.json`~~ → Diselesaikan: password kini disahkan melalui server (`admin_users` DB, hashed). `config.json` hanya fallback offline.
- QR code dijana semula setiap saat (boleh dioptimumkan)
- Matrix rain menggunakan tkinter Canvas -- prestasi bergantung pada spesifikasi PC
- ~~PythonAnywhere free tier perlu reload setiap 3 bulan~~ → Diselesaikan: paid plan ($10/bulan), tiada expiry
- Default superadmin `admin/admin` — **WAJIB tukar password** selepas deployment pertama

## Change Log
| Tarikh | Perubahan |
| :--- | :--- |
| 2026-02-06 | Backend migration PHP -> Flask, session limit 3 jam, countdown timer, auto-lock |
| 2026-02-06 | Automated test 26/26 PASS (100%) |
| 2026-02-06 | Ngrok dibuang sepenuhnya (fail, kod, rujukan). Cloudflare sahaja. `setup_wizard.py` DEFAULT_SERVER_URL dikemas kini. Header `ngrok-skip-browser-warning` dibuang dari `client.py`. |
| 2026-02-06 | **IP & MAC Logging**: DB schema ditambah `ip_address` + `mac_address`. Client hantar MAC via `getmac`. Server rekod IP dari request header. Admin panel + CSV export dikemas kini. |
| 2026-02-06 | **Matrix Digital Rain**: Animasi hujan aksara Katakana/hex pada latar belakang lock screen. Menggunakan tkinter Canvas layer. Berhenti semasa unlock, bermula semula semasa re-lock. |
| 2026-02-06 | **Rebranding**: 'Sistem Makmal KKP' -> 'Sistem Lab Sentinel', 'FKEKK' -> 'HelmiSoftTech' (dalam `server.py` dan `unlock.php`). |
| 2026-02-06 | **Transparent UI Layout**: Layout ditukar dari `pack(fill=BOTH)` ke `place()` supaya matrix rain nampak di seluruh skrin. Container frame besar dibuang. Header dan footer jadi strip nipis. Widget diletakkan secara individu. |
| 2026-02-06 | **Offline Mode Fix**: Buang perubahan bg merah (#450a0a). Matrix rain terus berjalan dalam offline mode. Butang offline guna `place()`. |
| 2026-02-06 | **Setup Wizard URL Fix**: Help text dikemas kini -- sebut Cloudflare Tunnel URL dan port 5000 (buang rujukan lama `/lab-system`). |
| 2026-02-06 | **Jawi Matrix Rain**: Aksara Katakana ditukar ke huruf Jawi Melayu (ا ب ت ث ج... چ ڠ ڤ ڽ ۏ) + nombor Arab (0-9). |
| 2026-02-06 | **Domain Purchased**: `labsentinel.xyz` dibeli via Shinjiru (RM6.90/tahun). Akaun Cloudflare didaftar. Nameserver pending tukar. |
| 2026-02-11 | **Named Tunnel Setup**: `cloudflared tunnel create labsentinel` (ID: e3992090-b77d-4b30-a943-fb74d7742a6b). DNS CNAME `lab.labsentinel.xyz` → tunnel. Config.yml dibuat. `start_cloudflare.bat` ditukar ke Named Tunnel. `config.json` dikemas kini ke `https://lab.labsentinel.xyz`. |
| 2026-02-11 | **Tunnel Test**: Server + Named Tunnel dijalankan. 4/4 endpoint diuji melalui `https://lab.labsentinel.xyz` — semua PASS (200 OK). Tunnel connect ke Cloudflare edge (kul01, sin14, sin13) via QUIC. |
| 2026-02-11 | **EXE Rebuild**: PyInstaller 6.18.0, Python 3.14.2. `LabSentinel Setup.exe` (19MB) + `LabSentinel Client.exe` (23MB). Build artifacts dibersihkan. |
| 2026-02-11 | **End-to-End Test**: 27/27 PASS (100%) melalui `https://lab.labsentinel.xyz`. |
| 2026-02-11 | **Padam PHP Legacy**: 5 fail dipadam (`api.php`, `config.php`, `init_db.php`, `unlock.php`, `test.php`). |
| 2026-02-11 | **Admin Password Update**: Ditukar dari `admin` ke password baru. EXE di-rebuild. |
| 2026-02-11 | **Deployment Package**: Folder `deploy/LabSentinel/` disediakan. |
| 2026-02-11 | **Post-Update Test**: 16/16 PASS (100%) — localhost + tunnel. |
| 2026-02-11 | **Clean Unlock View**: Selepas unlock, window kecil (420x280) hanya papar ACCESS GRANTED + countdown timer. Elemen lock screen (QR, arahan, matrix rain) disorokkan. |
| 2026-02-11 | **Admin Buttons**: Butang "Admin Panel" (buka browser → `/admin`) dan "Settings" (buka `config.json`) ditambah di unlock view. Kedua-dua dilindungi password. |
| 2026-02-11 | **Custom Window Icon**: `logo.ico` digunakan untuk title bar + taskbar via `iconbitmap()` + `ctypes.SetCurrentProcessExplicitAppUserModelID()`. |
| 2026-02-11 | **Multi-Lab Support**: Kolum `lab_name` ditambah dalam DB. Server simpan `lab_name` dari client register. Admin panel ada dropdown filter mengikut makmal. CSV export ikut filter. 7/7 multi-lab test PASS. |
| 2026-02-11 | **Admin Dashboard**: Admin panel ditukar ke 2-tab view — Tab "Dashboard PC" (grid visual PC per makmal, status LOCKED/UNLOCKED, pengguna semasa, statistik) + Tab "Log Pengguna" (jadual rekod + filter + CSV export). |
| 2026-02-11 | **Setup Wizard Simplify**: Dropdown makmal/PC dibuang. Pemilik makmal taip sendiri nama makmal dan nama PC melalui text field. Server URL pre-filled ke `https://lab.labsentinel.xyz`. |
| 2026-02-11 | **Final EXE Rebuild**: PyInstaller 6.18.0, Python 3.14.2. Setup (19MB) + Client (23MB). Deployment package dikemas kini dengan EXE terkini + logo.ico. |
| 2026-02-11 | **banner.png ditambah**: Fail banner.png ditambah ke pakej deploy (sebelum ni tertinggal). Tanpa fail ini Setup Wizard papar "BANNER MISSING". |
| 2026-02-11 | **Pakej disalin ke E:\Program**: Folder `LabSentinel` (7 fail: 2 EXE + config + logo.png + logo.ico + banner.png + INSTALL.txt) disalin ke `E:\Program\LabSentinel` untuk deploy manual ke PC makmal. |
| 2026-02-11 | **Server & Tunnel dihentikan**: Flask server dan Cloudflare tunnel dihentikan sementara. |
| 2026-02-11 | **Icon Fix (Setup Wizard)**: Tambah `ctypes.SetCurrentProcessExplicitAppUserModelID` dan `iconbitmap(logo.ico)` pada `setup_wizard.py`. Ikon bulu ayam Python ditukar ke logo LabSentinel di semua window. |
| 2026-02-11 | **Database Reset**: 32 rekod test data dibuang. Dashboard bermula kosong — hanya papar data dari PC yang betul-betul register. |
| 2026-02-11 | **Server + Tunnel dimulakan semula**: Flask server + Cloudflare tunnel aktif. Dashboard kosong disahkan berfungsi melalui tunnel. |
| 2026-02-11 | **Local Client Test**: Client dilancarkan via `client.py` — register PASS, polling PASS, QR scan PASS, unlock PASS, admin panel PASS. |
| 2026-02-12 | **PythonAnywhere Deployment**: Flask server di-deploy ke `labsentinel.xyz` (free tier, Python 3.9). `server.py` dikemas kini — DB path auto-detect PythonAnywhere (`~/labsentinel_data/`). `wsgi.py` dibuat. WSGI config, source directory, force HTTPS dikonfigurasi via API. Semua endpoint diuji — `/test` OK, `/admin` 200, `/` homepage OK. `config.json` dikemas kini ke URL baru. Cloudflare Tunnel deprecated. |
| 2026-02-12 | **EXE Rebuild + Deploy Update**: PyInstaller 6.18.0, Python 3.14.2. Setup (19MB) + Client (23MB) rebuild dengan URL baru. Deploy package (`deploy/LabSentinel/` + `E:\Program\LabSentinel`) dikemas kini — config.json, INSTALL.txt, kedua-dua EXE. |
| 2026-02-12 | **Phone QR Test PASS**: Unlock page dibuka dari phone (mobile data) → borang muncul → submit berjaya → "PC Berjaya Dibuka" → server confirm UNLOCKED. Full end-to-end 8/8 PASS. Masalah 503 selesai. |
| 2026-02-12 | **Admin Auto-Refresh**: Admin dashboard (`/admin`) auto-refresh setiap 60 saat via `<meta http-equiv="refresh">`. Server.py dikemas kini dan di-upload + reload di PythonAnywhere. |
| 2026-02-12 | **Icon Fix (EXE Bundle)**: `logo.ico` ditambah ke `--add-data` dalam build command untuk kedua-dua Setup dan Client EXE. Sebelum ini `logo.ico` hanya set sebagai `--icon` (ikon fail EXE di Explorer) tapi tak di-bundle dalam EXE, menyebabkan ikon bulu ayam Python muncul di title bar. `build_app.bat` dikemas kini. Kedua-dua EXE di-rebuild. |
| 2026-02-12 | **Setup Wizard URL Fix**: `DEFAULT_SERVER_URL` dalam `setup_wizard.py` ditukar dari `https://lab.labsentinel.xyz` ke `https://labsentinel.xyz`. |
| 2026-02-12 | **Icon Fix (EXE Bundle + Uninstall)**: `logo.ico` di-bundle dalam kedua-dua EXE via `--add-data`. Uninstall dialog icon diperbaiki — `iconbitmap(default=ico_path)` dipanggil sebelum `withdraw()` supaya child windows inherit ikon. `build_app.bat` dikemas kini. |
| 2026-02-12 | **Taskkill on Uninstall**: `taskkill /F /IM "LabSentinel Client.exe"` ditambah sebelum padam fail semasa uninstall. Program kini berhenti sepenuhnya sebelum folder dipadam. |
| 2026-02-12 | **Full Install/Uninstall Test PASS**: Setup wizard ikon OK, Installed Apps ikon OK, uninstall dialog ikon OK, taskkill berfungsi, folder dipadam bersih. |
| 2026-02-11 | **Proper Windows Installer**: Setup Wizard ditukar jadi installer penuh — install ke `C:\Program Files\LabSentinel\`, copy Client EXE + Setup EXE + logo + config, daftar dalam Windows Installed Apps (registry uninstall entry), startup shortcut point ke Program Files. Butang "Finish" ditukar ke "Install". |
| 2026-02-11 | **Password-Protected Uninstall**: Uninstall dari Installed Apps memerlukan admin password. Setup EXE menyokong `--uninstall` flag. Flow: minta password → sahkan → padam folder + shortcut + registry. Password salah = uninstall dibatalkan. |
| 2026-02-11 | **Client Config Search Path**: Client EXE cari config.json dari: exe directory → current dir → `C:\Program Files\LabSentinel\`. Sesuai dengan install location baru. |
| 2026-02-11 | **Full Install Test PASS**: Setup EXE dijalankan dari E:\Program — install ke Program Files berjaya, muncul dalam Installed Apps, semua fail tercopy. |

| 2026-02-13 | **Server-Side Admin Verification**: Endpoint baru `verify_admin` ditambah dalam `server.py`. Client (`client.py`) kini sahkan password admin melalui server (`admin_users` DB, hashed) — bukan lagi plaintext dari `config.json`. Fallback ke config hanya bila server tidak boleh dicapai (offline). Fungsi `verify_admin_password()` ditambah, digunakan oleh `admin_unlock()`, `open_admin_panel()`, `open_settings()`. |
| 2026-02-13 | **Admin Dashboard Role-Based UI**: Admin bar dikemas kini — Superadmin nampak badge "Superadmin" + butang "Urus Admin". Pentadbir Makmal nampak badge "Pentadbir Makmal" + senarai makmal seliaan. Subtitle bertukar mengikut peranan. Mesej khas jika admin tiada makmal ditugaskan. |
| 2026-02-13 | **Delete Lab Feature**: Superadmin boleh buang makmal dari halaman Urus Admin. Padam semua sesi + bersihkan assigned_labs admin. Dialog pengesahan dengan amaran kekal. Statistik PC dan rekod dipaparkan. |
| 2026-02-13 | **Domain Migration**: `linuxpredator.pythonanywhere.com` → `labsentinel.xyz`. PythonAnywhere paid plan ($10/bulan). DNS CNAME via Cloudflare (DNS only). Let's Encrypt SSL auto-renew. Semua URL dalam kod dikemas kini. |
| 2026-02-13 | **Logo pada Web Pages**: Route `/static/logo.png` ditambah. Logo LabSentinel dipaparkan di halaman login, unlock (borang pengguna), admin dashboard, dan halaman urus admin. |
| 2026-02-13 | **EXE Rebuild + Final Deploy**: Kedua-dua EXE di-rebuild dengan semua perubahan terkini (server-side admin verify, role-based UI, delete lab, domain migration, logo). Pakej lengkap (7 fail) disalin ke `E:\Program\LabSentinel` untuk deploy manual. |

## Next Steps
1. ~~**Upload `server.py` ke PythonAnywhere**~~ — DONE (2026-02-13)
2. **Tukar default superadmin password** — login `/admin` → Urus Admin → Tukar Password akaun `admin`
3. **Cipta akaun pentadbir makmal** — login sebagai superadmin → Urus Admin → Tambah Admin → tetapkan makmal
4. ~~**Rebuild EXE**~~ — DONE (2026-02-13): Setup (19MB) + Client (23MB) di `E:\Program\LabSentinel`
5. **Deploy ke PC makmal** — copy dari `E:\Program\LabSentinel` ke PC sasaran, jalankan Setup (Run as Admin)
6. **Test end-to-end** — pastikan admin unlock sahkan melalui server, setiap pentadbir hanya nampak makmal sendiri
7. **Deploy ke semua 31 PC** — setelah ujian berjaya, deploy ke PC CS00 - PC CS30
