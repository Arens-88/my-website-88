@echo off

echo Creating FBA Shipping Calculator installer...

if not exist "dist\fba_gui.exe" (
    echo Error: Cannot find executable file
    pause
    exit /b 1
)

mkdir "installer" 2>nul
copy "dist\fba_gui.exe" "installer\FBA费用计算器.exe"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\FBA费用计算器.lnk'); $Shortcut.TargetPath = '%~dp0\installer\FBA费用计算器.exe'; $Shortcut.Save()"
echo Installer created!
pause