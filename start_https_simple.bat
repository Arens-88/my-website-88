@echo off
cd /d "%~dp0"

REM Check if certificates exist
set "sslDir=D:\ssl_certs"
set "certFile=%sslDir%\server.crt"
set "keyFile=%sslDir%\server.key"

if not exist "%certFile%" (
    echo ERROR: Certificate file not found: %certFile%
    echo Please deploy certificate first using deployment tool
    pause
    exit /b 1
)

if not exist "%keyFile%" (
    echo ERROR: Private key file not found: %keyFile%
    echo Please deploy certificate first using deployment tool
    pause
    exit /b 1
)

echo Certificate check successful!

REM Stop any running Python processes
for /f "tokens=*" %%a in ('tasklist ^| findstr /i "python"') do (
    echo Stopping Python processes...
    taskkill /F /IM python.exe >nul 2>&1
    timeout /t 2 >nul
    goto continue
)
:continue

REM Start HTTPS server
"%cd%\..\python.exe" "%cd%\start_update_server.py" --https

pause