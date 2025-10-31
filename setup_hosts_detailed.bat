@echo on
cls
echo ===================================================
echo           详细版 Hosts 文件配置 - tomarens.xyz
setlocal enabledelayedexpansion

REM 创建日志文件
set LOG_FILE=%~dp0hosts_setup_log.txt
echo > %LOG_FILE%
echo 开始执行hosts配置脚本：%date% %time% >> %LOG_FILE%

REM 检查是否以管理员身份运行
echo 检查管理员权限...
echo 检查管理员权限... >> %LOG_FILE%
NET SESSION >nul 2>> %LOG_FILE%
if %errorLevel% neq 0 (
    echo 错误：请以管理员身份运行此脚本！ >> %LOG_FILE%
    echo 错误：请以管理员身份运行此脚本！
    echo 请右键点击此脚本，选择"以管理员身份运行"
    echo 按任意键退出...
    pause >nul
    exit /b 1
) else (
    echo 已确认管理员权限 >> %LOG_FILE%
    echo 已确认管理员权限
)

set HOSTS_FILE=C:\Windows\System32\drivers\etc\hosts
set DOMAIN=tomarens.xyz
set IP=127.0.0.1

echo 配置信息： >> %LOG_FILE%
echo Hosts文件路径：%HOSTS_FILE% >> %LOG_FILE%
echo 域名：%DOMAIN% >> %LOG_FILE%
echo 目标IP：%IP% >> %LOG_FILE%

REM 检查hosts文件是否存在
if not exist "%HOSTS_FILE%" (
    echo 错误：Hosts文件不存在！ >> %LOG_FILE%
    echo 错误：Hosts文件不存在！
    echo 请检查系统路径是否正确
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

REM 检查hosts文件中是否已存在条目
echo 正在检查hosts文件中是否已存在条目...
findstr /C:"%DOMAIN%" "%HOSTS_FILE%" >nul
if %errorLevel% equ 0 (
    echo 警告：hosts文件中已存在 %DOMAIN% 的条目！ >> %LOG_FILE%
    echo 警告：hosts文件中已存在 %DOMAIN% 的条目！
    set /p choice=是否覆盖现有条目？(Y/N): 
    echo 用户选择：%choice% >> %LOG_FILE%
    if /i "%choice%" neq "y" (
        echo 操作已取消。 >> %LOG_FILE%
        echo 操作已取消。
        echo 按任意键退出...
        pause >nul
        exit /b 0
    )
    REM 备份hosts文件
    echo 创建hosts文件备份...
    copy "%HOSTS_FILE%" "%HOSTS_FILE%.bak" >nul 2>> %LOG_FILE%
    if %errorLevel% equ 0 (
        echo 已创建hosts文件备份：%HOSTS_FILE%.bak >> %LOG_FILE%
        echo 已创建hosts文件备份：%HOSTS_FILE%.bak
    ) else (
        echo 警告：创建备份失败，但将继续操作 >> %LOG_FILE%
        echo 警告：创建备份失败，但将继续操作
    )
    REM 删除现有条目
    echo 删除现有条目...
    findstr /v /C:"%DOMAIN%" "%HOSTS_FILE%.bak" > "%TEMP%\newhosts.txt" 2>> %LOG_FILE%
    copy "%TEMP%\newhosts.txt" "%HOSTS_FILE%" >nul 2>> %LOG_FILE%
    if %errorLevel% equ 0 (
        echo 已删除现有条目 >> %LOG_FILE%
        echo 已删除现有条目
    ) else (
        echo 警告：删除现有条目失败 >> %LOG_FILE%
        echo 警告：删除现有条目失败
    )
)

REM 添加新条目
echo 添加 %DOMAIN% 到hosts文件...
echo.>> "%HOSTS_FILE%" 2>> %LOG_FILE%
echo %IP% %DOMAIN% >> "%HOSTS_FILE%" 2>> %LOG_FILE%

if %errorLevel% equ 0 (
    echo 成功：hosts文件已更新 >> %LOG_FILE%
    echo ===================================================
    echo 成功！hosts文件已配置：
    echo %IP% %DOMAIN%
    echo ===================================================
    echo 现在您可以通过以下地址访问服务器：
    echo - http://tomarens.xyz:8081
    echo - http://tomarens.xyz:8081/index.html
    echo ===================================================
    echo 详细日志已保存至：%LOG_FILE%
) else (
    echo 错误：无法更新hosts文件！ >> %LOG_FILE%
    echo 错误：无法更新hosts文件！
    echo 请检查文件权限或手动修改hosts文件
    echo 详细错误信息请查看日志：%LOG_FILE%
)

echo 脚本执行完成：%date% %time% >> %LOG_FILE%
echo ===================================================
echo 按任意键退出...
pause >nul