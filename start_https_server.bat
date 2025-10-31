@echo off
cd /d "%~dp0"
cls

echo ===================================================
echo            启动HTTPS更新服务器
 echo ===================================================
echo 此脚本将启动FBA费用计算器的HTTPS更新服务器
echo ===================================================

rem 检查SSL证书是否存在
set "sslDir=D:\ssl_certs"
set "certFile=%sslDir%\server.crt"
set "keyFile=%sslDir%\server.key"

echo 检查SSL证书文件...
if not exist "%certFile%" ( 
    echo 警告: 未找到SSL证书文件: %certFile%
    echo 正在检查备选证书文件...
    
    rem 检查备选证书文件
    if exist "%sslDir%\cert.pem" (
        echo 找到备选证书文件: %sslDir%\cert.pem
        set "certFile=%sslDir%\cert.pem"
    ) else (
        echo 错误: 未找到证书文件
        goto generate_cert
    )
)

if not exist "%keyFile%" ( 
    echo 警告: 未找到私钥文件: %keyFile%
    echo 正在检查备选私钥文件...
    
    rem 检查备选私钥文件
    if exist "%sslDir%\privkey.pem" (
        echo 找到备选私钥文件: %sslDir%\privkey.pem
        set "keyFile=%sslDir%\privkey.pem"
    ) else (
        echo 错误: 未找到私钥文件
        goto generate_cert
    )
)

:generate_cert
if not exist "%certFile%" if not exist "%keyFile%" (
    echo ===================================================
    echo 需要SSL证书才能启动HTTPS服务器
    echo 请先生成SSL证书
    echo ===================================================
    echo 按任意键运行证书生成脚本...
    pause >nul
    call "%~dp0生成SSL证书.bat"
    
    rem 重新检查证书
    if not exist "%certFile%" if not exist "%sslDir%\cert.pem" (
        echo 错误: 证书生成失败或仍未找到证书文件
        echo 建议使用HTTP模式代替
        echo 按任意键启动HTTP服务器...
        pause >nul
        call "%~dp0start_server.bat"
        exit /b 1
    )
)

echo 证书文件检查通过！
echo ===================================================
echo 正在启动HTTPS更新服务器...
echo 端口: 8443
if exist "%certFile%" echo 证书: %certFile%
if exist "%keyFile%" echo 私钥: %keyFile%
echo ===================================================

rem 启动HTTPS服务器
"%cd%\..\.conda\python.exe" "%cd%\launch_server.py" --https

rem 如果启动失败，尝试直接启动
if %errorLevel% neq 0 (
    echo 警告: 启动脚本执行失败，尝试直接启动服务器...
    "%cd%\..\.conda\python.exe" "%cd%\start_update_server.py" --https
)

echo 服务器启动完成！
pause