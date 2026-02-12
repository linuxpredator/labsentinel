# LabSentinel - Professional Edition
**Powered by HelmiSoftTech**

Sistem kunci pintar PC Makmal berasaskan QR Code dengan antaramuka profesional.

## 1. Persediaan Server (PHP)
1. Upload folder `lab-system` ke server anda.
2. Pastikan file permissions membenarkan server tulis ke `lab_system.db`.

## 2. Pemasangan Client (Windows)

### Langkah 1: Install Python & Library
Pastikan Python 3.x telah diinstall. Kemudian install library yang diperlukan:
```cmd
pip install requests qrcode pillow
```

### Langkah 2: Jalankan Setup Wizard
Kita tidak lagi perlu edit kod secara manual. Jalankan installer profesional kami:
```cmd
python setup_wizard.py
```
- Wizard akan membimbing anda untuk menetapkan **Nama Makmal**, **Nama PC**, dan **Admin Password**.
- Configuration akan disimpan secara automatik.

### Langkah 3: Jalankan Lock Screen
Selepas setup selesai, jalankan client:
```cmd
python client.py
```
- PC akan terkunci dengan paparan Fullscreen yang cantik ("Premium Dark Theme").
- Jam dan Tarikh akan dipaparkan.
- QR Code akan dijana untuk unlock.

## 3. Ciri-Ciri Tambahan
- **Admin Unlock**: Jika internet tiada atau QR code rosak, tekan **Ctrl + Alt + L** dan masukkan Admin Password yang anda tetapkan semasa setup.
- **Branding**: Logo rasmi LabSentinel dan watermark "HelmiSoftTech".

---
**Nota Teknikal:**
- Konfigurasi disimpan dalam `config.json`.
- Log disimpan secara lokal (jika diaktifkan).
