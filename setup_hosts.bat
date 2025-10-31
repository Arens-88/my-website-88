@echo off
cls
echo ===================================================
echo           配置Hosts文件 - tomarens.xyz
setlocal enabledelayedexpansion

REM 检查是否以管理员身份运行
NET SESSION >nul 2>&1
if %errorLevel% neq 0 (
    echo 错误：请以管理员身份运行此脚本！
    echo 请右键点击此脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

set HOSTS_FILE=C:\Windows\System32\drivers\etc\hosts
set DOMAIN=tomarens.xyz
set IP=127.0.0.1

REM 检查hosts文件中是否已存在条目
echo 正在检查hosts文件...
findstr /C:"%DOMAIN%" "%HOSTS_FILE%" >nul
if %errorLevel% equ 0 (
    echo 警告：hosts文件中已存在 %DOMAIN% 的条目！
    set /p choice=是否覆盖现有条目？(Y/N): 
    if /i "%choice%" neq "y" (
        echo 操作已取消。
        pause
        exit /b 0
    )
    REM 备份hosts文件
    copy "%HOSTS_FILE%" "%HOSTS_FILE%.bak" >nul
    echo 已创建hosts文件备份：%HOSTS_FILE%.bak
    REM 删除现有条目
    findstr /v /C:"%DOMAIN%" "%HOSTS_FILE%.bak" > "%HOSTS_FILE%"
    echo 已删除现有条目
)

REM 添加新条目
echo 添加 %DOMAIN% 到hosts文件...
echo.>> "%HOSTS_FILE%"
echo %IP% %DOMAIN% >> "%HOSTS_FILE%"

if %errorLevel% equ 0 (
    echo ===================================================
    echo 成功！hosts文件已配置：
    echo %IP% %DOMAIN%
    echo ===================================================
    echo 现在您可以通过以下地址访问服务器：
    echo - http://tomarens.xyz:8081
    echo - http://tomarens.xyz:8081/index.html
    echo ===================================================
    echo 注意：请确保Python服务器正在端口8081上运行！
) else (
    echo 错误：无法更新hosts文件！
)

pause