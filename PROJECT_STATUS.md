# LabSentinel Project Status
**Last Updated**: 2026-02-11 (Proper Installer + Uninstall Password Protection + All Tests PASS)

## Current Phase: TESTING & DEPLOYMENT

## System Status Overview
| Component | Status | Tested | Notes |
| :--- | :--- | :--- | :--- |
| **Client App** (`client.py`) | **Operational** | GUI PASS | Fullscreen lock screen, QR unlock, 3-jam session limit + clean unlock view + Matrix Digital Rain + logo.ico icon |
| **Server API** (`server.py`) | **Operational** | 16/16 PASS | Python Flask backend pada port 5000, multi-lab support |
| **Setup Wizard** (`setup_wizard.py`) | **Operational** | PASS | Installer penuh: install ke `C:\Program Files\LabSentinel`, daftar Installed Apps, uninstall dilindungi password |
| **Build System** (`build_app.bat`) | **Operational** | - | PyInstaller build script, menghasilkan .exe |
| **Remote Access - Cloudflare** | **Operational** | 4/4 PASS | Named Tunnel `labsentinel` → `lab.labsentinel.xyz` (ID: e3992090-b77d-4b30-a943-fb74d7742a6b) |
| **Admin Panel** (`/admin`) | **Operational** | PASS | **Dashboard PC** (grid visual per makmal) + **Log Pengguna** (jadual + filter + CSV export) |
| **Built Executables** (`dist/`) | **Up-to-date** | - | Rebuild 2026-02-11: Setup (19MB, installer + uninstaller) + Client (23MB, config search path) |
| **Deployment Package** (`deploy/`) | **Up-to-date** | - | Folder siap copy: EXE + config + logo + logo.ico + banner.png + INSTALL.txt |
| **Deploy Location** (`E:\Program\LabSentinel`) | **Copied** | - | Pakej lengkap disalin ke E:\Program untuk deploy manual ke PC makmal |
| **Database** (`lab_system.db`) | **Clean** | - | Test data dibuang — dashboard bermula kosong, data masuk mengikut PC yang register |

## Domain & Tunnel Setup
| Item | Status | Detail |
| :--- | :--- | :--- |
| **Domain** | **Purchased** | `labsentinel.xyz` via Shinjiru (RM6.90/tahun) |
| **Cloudflare Account** | **Created** | `Linuxpredator@gmail.com` |
| **Nameserver** | **Active** | Cloudflare NS aktif |
| **Named Tunnel** | **Created** | ID: `e3992090-b77d-4b30-a943-fb74d7742a6b`, route `lab.labsentinel.xyz` → Flask :5000 |
| **DNS CNAME** | **Active** | `lab.labsentinel.xyz` → tunnel `labsentinel` |

### Target Configuration (Selepas Setup Siap)
```json
{
    "lab_name": "General Lab",
    "pc_name": "PC-01",
    "admin_password": "<password>",
    "server_url": "https://lab.labsentinel.xyz",
    "auto_start": true
}
```
> **URL tetap** - tidak berubah walaupun tunnel restart. Semua client PC guna URL yang sama selamanya.

### Setup Checklist
- [x] Beli domain `labsentinel.xyz` (Shinjiru - RM6.90)
- [x] Daftar akaun Cloudflare (Free plan)
- [x] Tambah `labsentinel.xyz` ke Cloudflare dashboard
- [x] Tukar nameserver di Shinjiru ke Cloudflare NS
- [x] DNS propagation selesai (status: Active)
- [x] Install `cloudflared` dan login pada PC server makmal
- [x] Buat Named Tunnel (`cloudflared tunnel create labsentinel`) — ID: `e3992090-b77d-4b30-a943-fb74d7742a6b`
- [x] Route subdomain `lab.labsentinel.xyz` → `localhost:5000`
- [x] Update `config.json` — server_url: `https://lab.labsentinel.xyz`
- [x] Update `start_cloudflare.bat` untuk guna Named Tunnel
- [x] Ujian end-to-end: 27/27 PASS via `https://lab.labsentinel.xyz` (API + validation + unlock + admin + CSV)

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
    lab_name        TEXT,              -- BARU: Nama makmal untuk multi-lab filter
    unlock_time     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
)
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
| `start_cloudflare.bat` | Tool | **Active** | Cloudflare tunnel starter |
| `cloudflared.exe` | Binary | **Present** | Cloudflare tunnel executable |
| `logo.png` | Asset | **Present** | App logo |
| `logo.ico` | Asset | **Present** | Windows icon (title bar + taskbar) |
| `banner.png` | Asset | **Present** | Setup wizard sidebar banner |
| `dist/` | Output | **Up-to-date** | Rebuild 2026-02-11: Setup (19MB) + Client (23MB) |
| `deploy/LabSentinel/` | Output | **Up-to-date** | Pakej deployment: EXE + config.json + logo.png + logo.ico + INSTALL.txt |

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
- [ ] Multi-PC serentak berfungsi
- [x] Cloudflare Named Tunnel berfungsi dari rangkaian luar
- [x] Ikon LabSentinel pada title bar window
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
- [x] **Rebranding**: 'Sistem Makmal KKP' -> 'Sistem Lab Sentinel', 'FKEKK' -> 'HelmiSoftTech'
- [x] **Transparent UI**: Layout `place()` supaya matrix rain nampak penuh di latar belakang
- [x] **Domain Purchased**: `labsentinel.xyz` dibeli via Shinjiru (RM6.90/tahun)
- [x] **Named Cloudflare Tunnel**: URL tetap `lab.labsentinel.xyz` (Tunnel ID: e3992090-b77d-4b30-a943-fb74d7742a6b)
- [x] **Deployment Package**: Folder `deploy/LabSentinel/` sedia untuk copy ke PC ujian

## Architecture
```
                    INTERNET
                       |
            [lab.labsentinel.xyz]     <-- URL tetap (Named Tunnel)
                       |
              [Cloudflare Edge]
                       |
              [cloudflared tunnel]    <-- PC Server Makmal
                       |
              [Flask Server :5000]
              /        |        \
         /api.php   /unlock.php  /admin
         (register,  (user form)  (records +
          check,                   CSV export,
          IP/MAC,                  multi-lab filter)
          lab_name)
              |
         [SQLite DB]
         (sessions + IP + MAC + lab_name)
              |
    [Lab A]         [Lab B]         [Lab N]
    PC-01..PC-N     PC-01..PC-N     PC-01..PC-N
    (Lock Screen)   (Lock Screen)   (Lock Screen)
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
1. Double-click `START_ALL.bat`
2. URL tetap: `https://lab.labsentinel.xyz` (Named Tunnel — tiada perlu salin URL)
3. Pastikan `config.json` pada setiap PC client ada `"server_url": "https://lab.labsentinel.xyz"`
4. Set `"lab_name"` mengikut makmal (contoh: "Lab Multimedia", "Lab Cyber Security")
5. Jalankan client pada setiap PC

### Build Executables
1. Double-click `build_app.bat`
2. Output: `dist/LabSentinel Setup.exe` + `dist/LabSentinel Client.exe`

## Known Issues / Notes
- ~~Fail PHP deprecated~~ → Dipadam 2026-02-11
- ~~URL Cloudflare Tunnel berubah setiap kali dimulakan semula~~ → Diselesaikan dengan Named Tunnel (`lab.labsentinel.xyz`)
- Admin password disimpan dalam plaintext di `config.json`
- QR code dijana semula setiap saat (boleh dioptimumkan)
- Matrix rain menggunakan tkinter Canvas -- prestasi bergantung pada spesifikasi PC

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
| 2026-02-11 | **Proper Windows Installer**: Setup Wizard ditukar jadi installer penuh — install ke `C:\Program Files\LabSentinel\`, copy Client EXE + Setup EXE + logo + config, daftar dalam Windows Installed Apps (registry uninstall entry), startup shortcut point ke Program Files. Butang "Finish" ditukar ke "Install". |
| 2026-02-11 | **Password-Protected Uninstall**: Uninstall dari Installed Apps memerlukan admin password. Setup EXE menyokong `--uninstall` flag. Flow: minta password → sahkan → padam folder + shortcut + registry. Password salah = uninstall dibatalkan. |
| 2026-02-11 | **Client Config Search Path**: Client EXE cari config.json dari: exe directory → current dir → `C:\Program Files\LabSentinel\`. Sesuai dengan install location baru. |
| 2026-02-11 | **Full Install Test PASS**: Setup EXE dijalankan dari E:\Program — install ke Program Files berjaya, muncul dalam Installed Apps, semua fail tercopy. |

## Next Steps
1. **Deploy ke PC makmal** - copy `E:\Program\LabSentinel` ke PC sasaran, jalankan Setup (Run as Admin)
2. **Test end-to-end dari PC makmal** - pastikan install, lock screen, QR scan, unlock, admin panel, dan uninstall berfungsi
3. **Deploy ke semua 31 PC** - setelah ujian berjaya, deploy ke PC CS00 - PC CS30 dalam Makmal Cyber Security
