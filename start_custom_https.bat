@echo off
cd /d "%~dp0"
cls

echo ===================================================
echo            自定义HTTPS服务器启动脚本
 echo ===================================================
echo 此脚本将使用您已有的SSL证书启动HTTPS更新服务器
echo ===================================================

rem 证书默认路径
set "sslDir=D:\ssl_certs"
set "certFile=%sslDir%\server.crt"
set "keyFile=%sslDir%\server.key"

echo 检测SSL证书目录...
if not exist "%sslDir%" (
    echo SSL证书目录不存在，创建目录: %sslDir%
    mkdir "%sslDir%"
)

:check_certificates
rem 检查证书文件是否存在
if not exist "%certFile%" (
    echo 未找到默认证书文件: %certFile%
    echo 请将您的证书文件放在 %sslDir% 目录下，命名为 server.crt
    echo 或在下面输入证书文件的完整路径
    set /p certFile="请输入证书文件路径: "
    if not exist "%certFile%" (
        echo 错误: 证书文件不存在！
        goto check_certificates
    )
)

if not exist "%keyFile%" (
    echo 未找到默认私钥文件: %keyFile%
    echo 请将您的私钥文件放在 %sslDir% 目录下，命名为 server.key
    echo 或在下面输入私钥文件的完整路径
    set /p keyFile="请输入私钥文件路径: "
    if not exist "%keyFile%" (
        echo 错误: 私钥文件不存在！
        goto check_certificates
    )
)

echo ===================================================
echo 证书文件检测通过！
echo 证书路径: %certFile%
echo 私钥路径: %keyFile%
echo ===================================================

rem 停止当前可能运行的服务器进程
echo 正在检查并停止当前运行的服务器进程...
tasklist | findstr /i "python" >nul
if %errorLevel% equ 0 (
    echo 发现Python进程，尝试停止...
    taskkill /F /IM python.exe >nul 2>&1
    echo 等待2秒...
    timeout /t 2 >nul
)

echo 正在启动HTTPS更新服务器...
echo 端口: 8443
echo ===================================================

rem 启动HTTPS服务器
python launch_server.py --https

rem 如果启动失败，尝试直接启动
if %errorLevel% neq 0 (
    echo 警告: 启动脚本执行失败，尝试直接启动服务器...
    python start_update_server.py --https
)

echo ===================================================
echo 服务器启动完成！
echo 您可以通过以下地址访问:
echo - https://localhost:8443
echo - https://tomarens.xyz:8443
echo ===================================================
echo 注意: 请确保Windows防火墙允许端口8443的访问
pause