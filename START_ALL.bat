@echo off
title LabSentinel Launcher
color 0E

echo ==================================================
echo      LABSENTINEL - SYSTEM LAUNCHER
echo ==================================================
echo.

echo [1/2] Memulakan Python Server...
start "LabSentinel Server" cmd /k "cd /d "%~dp0" && start_server.bat"

:: Tunggu server start
timeout /t 3 /nobreak >nul

echo [2/2] Memulakan Cloudflare Tunnel...
start "LabSentinel Cloudflare" cmd /k "cd /d "%~dp0" && start_cloudflare.bat"

echo.
echo ==================================================
echo    KEDUA-DUA SERVIS TELAH DIMULAKAN
echo ==================================================
echo.
echo Server:  http://localhost:5000
echo Tunnel:  https://lab.labsentinel.xyz (Named Tunnel)
echo.
echo URL tetap - tidak perlu salin/tukar config.json
echo.
pause
