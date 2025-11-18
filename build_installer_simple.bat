@echo off

ECHO Building FBA calculator installer...
ECHO Using fixed installer.py

REM Ensure dist directory exists
mkdir dist 2>nul

REM Build installer with PyInstaller
python -m PyInstaller installer.spec
if %errorlevel% neq 0 (
    ECHO Installer build failed!
    pause
    exit /b %errorlevel%
)

ECHO Installer built successfully!
ECHO Executable generated at dist\FBA费用计算器安装程序.exe
ECHO.  
ECHO Please copy the generated installer to the website download page

pause