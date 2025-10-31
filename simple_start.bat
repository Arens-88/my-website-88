@echo off
cd /d "%~dp0"
cls
echo ===================================================
echo            FBA费用计算器更新服务器
echo ===================================================
echo 正在启动服务器，请稍候...
echo 服务器地址: http://localhost:8081
echo 域名访问: http://tomarens.xyz:8081
echo 更新页面: http://localhost:8081/index.html
echo 域名更新页面: http://tomarens.xyz:8081/index.html
echo ===================================================
echo 按 Ctrl+C 停止服务器
echo ===================================================
python -m http.server 8081
pause