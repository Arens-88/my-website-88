@echo off
cls

echo ======================================================
echo          FBA费用计算器程序签名工具
 echo ======================================================
echo 注意：使用此脚本前，您需要先购买代码签名证书并安装
echo 证书通常为.pfx格式文件，您需要知道证书的密码
 echo ======================================================
pause

:input
set /p CERT_PATH=请输入代码签名证书(.pfx)的完整路径: 
set /p CERT_PASS=请输入证书密码: 
set /p APP_PATH=请输入要签名的程序路径(默认为dist\FBA费用计算器安装程序.exe): 

:: 设置默认程序路径
if "%APP_PATH%"=="" set APP_PATH=dist\FBA费用计算器安装程序.exe

:: 检查文件是否存在
if not exist "%CERT_PATH%" (
    echo 错误：找不到证书文件 "%CERT_PATH%"
    goto input
)

if not exist "%APP_PATH%" (
    echo 错误：找不到程序文件 "%APP_PATH%"
    goto input
)

:: 检查signtool是否可用
signtool >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到signtool.exe，请确保已安装Windows SDK并将其添加到系统PATH
    echo 您可以从以下位置找到signtool.exe：
    echo - C:\Program Files (x86)\Windows Kits\10\bin\10.0.xxxxx.0\x64\signtool.exe
    echo - C:\Program Files (x86)\Windows Kits\8.1\bin\x64\signtool.exe
    echo 请手动设置signtool路径或安装Windows SDK
    pause
    exit /b 1
)

echo.
echo 开始签名程序...
echo 证书路径: %CERT_PATH%
echo 程序路径: %APP_PATH%
echo.

:: 执行签名命令
signtool sign /f "%CERT_PATH%" /p "%CERT_PASS%" "%APP_PATH%"

if %errorlevel% equ 0 (
    echo.
    echo ======================================================
    echo                    签名成功！
    echo ======================================================
    echo 程序已成功添加数字签名，现在可以正常运行而不会被SmartScreen拦截
    echo ======================================================
) else (
    echo.
    echo ======================================================
    echo                    签名失败！
    echo ======================================================
    echo 请检查证书路径、密码是否正确，或是否有权限使用此证书
    echo ======================================================
)

pause
