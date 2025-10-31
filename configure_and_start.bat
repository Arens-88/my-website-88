@echo off
cd /d "%~dp0"
cls

echo ===================================================
echo            配置域名和启动服务器
echo ===================================================
echo 此脚本将：
echo 1. 配置hosts文件，将tomarens.xyz映射到本地IP
echo 2. 启动FBA费用计算器更新服务器
echo ===================================================

rem 检查是否以管理员身份运行
NET SESSION >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员身份运行此脚本以配置hosts文件！
    echo 请右键点击此脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo 正在配置hosts文件...
call setup_hosts.bat

if %errorLevel% equ 0 (
    echo hosts文件配置成功！
    echo.    
    echo 正在启动更新服务器...
    echo ===================================================
    echo 服务器启动后，您可以通过以下地址访问：
    echo - 本地访问: http://localhost:8081
    echo - 域名访问: http://tomarens.xyz:8081
    echo ===================================================
    echo 请确保Windows防火墙允许端口8081的访问
    echo ===================================================
    
    rem 启动服务器
    python start_update_server.py
) else (
    echo hosts文件配置失败！
    echo 请检查权限或手动配置hosts文件。
    pause
    exit /b 1
)