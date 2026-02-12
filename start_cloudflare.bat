@echo off
title LabSentinel Tunnel (Cloudflare Named Tunnel)
color 0B

echo ==================================================
echo      LABSENTINEL NAMED TUNNEL (Cloudflare)
echo ==================================================
echo.

if not exist cloudflared.exe (
    echo [ERROR] cloudflared.exe tidak dijumpai!
    pause
    exit /b
)

echo [INFO] Memulakan Cloudflare Named Tunnel...
echo [INFO] URL tetap: https://lab.labsentinel.xyz
echo [INFO] Tunnel ID: e3992090-b77d-4b30-a943-fb74d7742a6b
echo.
echo Tekan Ctrl+C untuk berhenti.
echo.
echo ==================================================
echo.

cloudflared.exe tunnel --config "C:\Users\SU\.cloudflared\config.yml" run labsentinel

pause
