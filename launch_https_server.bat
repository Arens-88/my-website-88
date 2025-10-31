@echo off
cd /d "%~dp0"

REM Certificate directory
set "sslDir=D:\ssl_certs"

REM Start HTTPS server with .conda Python
"%cd%\..\.conda\python.exe" "%cd%\start_update_server.py" --https

pause