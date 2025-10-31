@echo off
cd /d "%~dp0"

ECHO ===================================================
ECHO            SSL Certificate Deployment Tool
ECHO ===================================================
ECHO This tool will help you deploy SSL certificates and start HTTPS server
ECHO ===================================================

REM Certificate target directory
set "sslDir=D:\ssl_certs"

REM Create SSL directory if it doesn't exist
ECHO Creating SSL certificate directory...
mkdir "%sslDir%" 2>nul

:input_cert_path
REM Get certificate file path
set /p certPath="Enter your SSL certificate file path: "
if not exist "%certPath%" (
    ECHO ERROR: Certificate file does not exist!
    goto input_cert_path
)

:input_key_path
REM Get private key file path
set /p keyPath="Enter your private key file path: "
if not exist "%keyPath%" (
    ECHO ERROR: Private key file does not exist!
    goto input_key_path
)

ECHO ===================================================
ECHO Copying certificate files...

REM Copy certificate file to target location
copy "%certPath%" "%sslDir%\server.crt" >nul
if %errorLevel% equ 0 (
    ECHO Certificate file copied successfully: %sslDir%\server.crt
) else (
    ECHO ERROR: Failed to copy certificate file!
    pause
    exit /b 1
)

REM Copy private key file to target location
copy "%keyPath%" "%sslDir%\server.key" >nul
if %errorLevel% equ 0 (
    ECHO Private key file copied successfully: %sslDir%\server.key
) else (
    ECHO ERROR: Failed to copy private key file!
    pause
    exit /b 1
)

ECHO ===================================================
ECHO Certificate deployment completed!
ECHO Certificate path: %sslDir%\server.crt
ECHO Private key path: %sslDir%\server.key

ECHO Stopping currently running server processes...
tasklist | findstr /i "python" >nul
if %errorLevel% equ 0 (
    ECHO Found Python processes, attempting to stop...
    taskkill /F /IM python.exe >nul 2>&1
    ECHO Waiting 2 seconds...
    timeout /t 2 >nul
)

ECHO Starting HTTPS update server...

ECHO You can choose the following options:
ECHO 1. Start HTTP server (no certificate required)
ECHO 2. Start HTTPS server (using deployed certificate)

set sel=
set /p sel="Please select an option (1-2): "

if "%sel%" equ "1" (
    ECHO Starting HTTP server...
    "%cd%\..\.conda\python.exe" "%cd%\start_update_server.py"
) else if "%sel%" equ "2" (
    ECHO Starting HTTPS server...
    "%cd%\..\.conda\python.exe" "%cd%\start_update_server.py" --https
) else (
    ECHO Invalid selection, defaulting to HTTPS server...
    "%cd%\..\.conda\python.exe" "%cd%\start_update_server.py" --https
)

pause