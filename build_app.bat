@echo off
title LabSentinel Builder
color 0A

echo ==================================================
echo      LABSENTINEL PROFESSIONAL BUILDER
echo      Powered by HelmiSoftTech
echo ==================================================
echo.

echo [INFO] Sedang memeriksa Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] Python tidak dijumpai!
    echo Sila install Python 3.x dari python.org dan pastikan option "Add to PATH" ditanda.
    echo.
    pause
    exit /b
)

echo [INFO] Python versi OK. Memulakan proses...
echo.

echo [1/5] Installing Dependencies (PyInstaller, etc)...
pip install pyinstaller pillow requests qrcode
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Gagal install library. Check internet connection.
    pause
    exit /b
)

echo.
echo [2/5] Creating Application Icon...
python -c "from PIL import Image; img = Image.open('logo.png'); img.save('logo.ico', format='ICO', sizes=[(256, 256)])"

echo.
echo [3/5] Building Installer (Setup Wizard)...
python -m PyInstaller --noconfirm --onefile --windowed --icon=logo.ico --add-data "banner.png;." --add-data "logo.png;." --name "LabSentinel Setup" setup_wizard.py

echo.
echo [4/5] Building Client (Lock Screen)...
python -m PyInstaller --noconfirm --onefile --windowed --icon=logo.ico --add-data "logo.png;." --name "LabSentinel Client" client.py

echo.
echo [5/5] Cleaning up build files...
rmdir /s /q build
del /q *.spec

echo.
echo ==================================================
echo  TAHNIAH! PROSES SELESAI.
echo ==================================================
echo.
echo Fail .exe anda berada di dalam folder 'dist':
echo 1. dist\LabSentinel Setup.exe
echo 2. dist\LabSentinel Client.exe
echo.
echo Anda boleh copy folder 'dist' ini ke dalam Pendrive untuk install di PC lain.
echo.
pause
