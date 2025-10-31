@echo off
cd /d "%~dp0"
cls

echo ===================================================
echo               One-Click Server Launcher

echo ===================================================
echo This script will start all servers required for FBA Fee Calculator

echo ===================================================

rem Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Warning: Running as administrator is recommended for necessary file operations
    echo Press any key to continue...
    pause >nul
)

rem SSL certificate directory
set "sslDir=D:\ssl_certs"

rem Stop existing Python processes
echo Stopping existing server processes...
tasklist | findstr /i "python" >nul
if %errorLevel% equ 0 (
    echo Python processes found, attempting to stop...
    taskkill /F /IM python.exe >nul 2>&1
    echo Waiting 3 seconds...
    timeout /t 3 >nul
)

rem Check if certificates exist
set "certExists=false"
if exist "%sslDir%\server.crt" if exist "%sslDir%\server.key" (
    set "certExists=true"
    echo SSL certificates found: server.crt and server.key
) else (
    echo Warning: SSL certificates not found in %sslDir%
)

rem Start only the main HTTPS server (since both servers may use the same port)
echo Starting main HTTPS server with certificates...
start "FBA HTTPS Server" cmd /c "cd /d %cd% && "%cd%\..\.conda\python.exe" "%cd%\launch_server.py" --https && pause"

rem Wait for server to initialize
echo Waiting for server to start...
timeout /t 5 >nul

rem Test if server is running
echo Testing server connectivity...
ping 127.0.0.1 -n 1 >nul

rem Display access information
echo ===================================================
echo Server startup completed!
echo ===================================================
echo Access addresses:
echo Local access:
echo   - https://localhost:8443
echo   - https://tomarens.xyz:8443
echo LAN access:
echo   - https://100.67.10.9:8443
echo ===================================================
echo Important notes:
echo 1. Ensure Windows Firewall allows access on port 8443
echo 2. For self-signed certificates, you may need to accept the security warning in your browser
echo 3. External access requires proper port forwarding on your router

echo ===================================================
echo Opening browser to test access...
start "" https://localhost:8443

pause