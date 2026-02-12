@echo off
title LabSentinel Server
color 0A

echo ==================================================
echo      LABSENTINEL SERVER (Python Flask)
echo ==================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak dijumpai!
    echo Sila install Python dari: https://python.org/downloads
    pause
    exit /b
)

:: Check and install Flask if needed
echo [INFO] Memeriksa dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [INFO] Memasang Flask...
    pip install flask
)

echo.
echo [INFO] Memulakan LabSentinel Server...
echo [INFO] Server URL: http://localhost:5000
echo [INFO] Tekan Ctrl+C untuk berhenti
echo.
echo ==================================================
echo.

cd /d "%~dp0"
python server.py

pause
