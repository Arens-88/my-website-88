@echo off
cd /d "%~dp0"

echo 开始启动HTTPS服务器...
echo 当前目录: %cd%
echo Python路径: D:\FBA\fba\.conda\python.exe

rem 停止可能正在运行的Python进程
echo 停止现有Python进程...
taskkill /F /IM python.exe >nul 2>&1

rem 等待进程完全停止
timeout /t 1 >nul

rem 创建日志文件
echo 启动服务器并记录日志...
"D:\FBA\fba\.conda\python.exe" start_update_server.py --https > server_startup.log 2>&1

rem 显示日志文件内容
echo 服务器启动日志:
type server_startup.log

echo.
echo 服务器启动完成，日志已保存到 server_startup.log