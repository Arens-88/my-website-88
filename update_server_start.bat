@echo off
cls
echo 正在启动FBA费用计算器更新服务器...
echo.

:: 检查Python是否可用
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请确保已安装Python并添加到环境变量
    pause
    exit /b 1
)

:: 启动服务器
python start_update_server.py

pause