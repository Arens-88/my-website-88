@echo off
cd /d "%~dp0"
cls

echo ===================================================
echo              域名更新完成!
echo ===================================================
echo 服务器域名已更换为 tomarens.xyz:8081

echo 
set /p choice=是否启动更新服务器? (Y/N): 
if /i "%choice%" neq "y" (
    echo 操作已取消。
    pause
    exit /b
)

echo 
echo 正在启动更新服务器...
echo ===================================================
echo 服务器地址:
echo - 本地访问: http://localhost:8081
echo - 域名访问: http://tomarens.xyz:8081
echo 
echo 更新页面:
echo - 本地访问: http://localhost:8081/index.html
echo - 域名访问: http://tomarens.xyz:8081/index.html
echo ===================================================
echo 

REM 启动Python服务器
python -m http.server 8081