@echo off
cls
echo ======================================================
echo        FBA网站性能优化 - Windows手动部署辅助工具
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
setlocal enabledelayedexpansion

:MENU
cls
echo ======================================================
echo        FBA网站性能优化 - Windows手动部署辅助工具
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 请选择要执行的操作：
echo.
echo [1] 查看服务器配置信息
echo [2] 上传优化文件（Nginx配置和Python脚本）
echo [3] 备份当前服务器配置
echo [4] 应用Nginx优化配置
echo [5] 部署优化版Python服务器
echo [6] 检查服务状态
echo [7] 查看日志文件
echo [8] 执行回滚操作
echo [9] 退出
echo.

set /p choice=请输入选项 [1-9]: 

if "!choice!"=="1" goto CHECK_SERVER
if "!choice!"=="2" goto UPLOAD_FILES
if "!choice!"=="3" goto BACKUP_CONFIG
if "!choice!"=="4" goto APPLY_NGINX
if "!choice!"=="5" goto DEPLOY_PYTHON
if "!choice!"=="6" goto CHECK_STATUS
if "!choice!"=="7" goto VIEW_LOGS
if "!choice!"=="8" goto ROLLBACK
if "!choice!"=="9" goto EXIT

call :SetColor 0C
echo 无效的选项，请重新输入！
echo.
call :SetColor 0F
pause
goto MENU

:CHECK_SERVER
cls
echo ======================================================
echo        查看服务器配置信息
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 正在连接服务器并检查配置...
echo 请确保您已将SSH密钥添加到服务器或准备好输入密码
echo.
echo 执行命令：ssh root@47.98.248.238 "find /etc/nginx -type f -name '*.conf' && echo '---' && ls -l /etc/nginx/sites-enabled/ && echo '---' && ls -la /var/www/"
call :SetColor 0A
echo 按任意键继续（或按Ctrl+C取消）...
echo.
call :SetColor 0F
pause >nul
ssh root@47.98.248.238 "find /etc/nginx -type f -name '*.conf' && echo '---' && ls -l /etc/nginx/sites-enabled/ && echo '---' && ls -la /var/www/"
echo.
pause
goto MENU

:UPLOAD_FILES
cls
echo ======================================================
echo        上传优化文件
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 正在上传优化文件到服务器...
echo.
echo 1. 上传Nginx配置文件
echo 执行命令：scp optimized_fba_app.conf root@47.98.248.238:/etc/nginx/sites-available/
echo.
echo 2. 上传Python服务器脚本
echo 执行命令：scp optimized_run_server.py root@47.98.248.238:/var/www/fba_app/
echo.
call :SetColor 0A
echo 按任意键继续（或按Ctrl+C取消）...
echo.
call :SetColor 0F
pause >nul

if not exist "optimized_fba_app.conf" (
    call :SetColor 0C
echo 错误：optimized_fba_app.conf 文件不存在！
    call :SetColor 0F
    pause
    goto MENU
)

if not exist "optimized_run_server.py" (
    call :SetColor 0C
echo 错误：optimized_run_server.py 文件不存在！
    call :SetColor 0F
    pause
    goto MENU
)

call :SetColor 0A
echo 开始上传Nginx配置文件...
echo.
call :SetColor 0F
scp optimized_fba_app.conf root@47.98.248.238:/etc/nginx/sites-available/
if errorlevel 1 (
    call :SetColor 0C
echo Nginx配置文件上传失败！
    call :SetColor 0F
    pause
    goto MENU
)

echo.
call :SetColor 0A
echo Nginx配置文件上传成功！
echo 开始上传Python服务器脚本...
echo.
call :SetColor 0F
scp optimized_run_server.py root@47.98.248.238:/var/www/fba_app/
if errorlevel 1 (
    call :SetColor 0C
echo Python服务器脚本上传失败！
    call :SetColor 0F
    pause
    goto MENU
)

echo.
call :SetColor 0A
echo 所有文件上传成功！
call :SetColor 0F
pause
goto MENU

:BACKUP_CONFIG
cls
echo ======================================================
echo        备份当前服务器配置
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 正在连接服务器并备份配置...
echo.
echo 执行命令：ssh root@47.98.248.238 "if [ -f '/etc/nginx/sites-available/fba_app.conf' ]; then cp /etc/nginx/sites-available/fba_app.conf /etc/nginx/sites-available/fba_app.conf.bak; echo 'Nginx配置已备份'; else echo 'Nginx配置文件不存在，无需备份'; fi && if [ -f '/var/www/fba_app/run_server.py' ]; then cp /var/www/fba_app/run_server.py /var/www/fba_app/run_server.py.bak; echo '服务器脚本已备份'; else echo '服务器脚本不存在，无需备份'; fi"
echo.
call :SetColor 0A
echo 按任意键继续（或按Ctrl+C取消）...
echo.
call :SetColor 0F
pause >nul
ssh root@47.98.248.238 "if [ -f '/etc/nginx/sites-available/fba_app.conf' ]; then cp /etc/nginx/sites-available/fba_app.conf /etc/nginx/sites-available/fba_app.conf.bak; echo 'Nginx配置已备份'; else echo 'Nginx配置文件不存在，无需备份'; fi && if [ -f '/var/www/fba_app/run_server.py' ]; then cp /var/www/fba_app/run_server.py /var/www/fba_app/run_server.py.bak; echo '服务器脚本已备份'; else echo '服务器脚本不存在，无需备份'; fi"
echo.
pause
goto MENU

:APPLY_NGINX
cls
echo ======================================================
echo        应用Nginx优化配置
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 正在应用Nginx优化配置...
echo.
echo 执行命令：ssh root@47.98.248.238 "mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled && rm -f /etc/nginx/sites-enabled/* && ln -s /etc/nginx/sites-available/optimized_fba_app.conf /etc/nginx/sites-enabled/ && nginx -t && service nginx restart && service nginx status"
echo.
call :SetColor 0A
echo 按任意键继续（或按Ctrl+C取消）...
echo.
call :SetColor 0F
pause >nul
ssh root@47.98.248.238 "mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled && rm -f /etc/nginx/sites-enabled/* && ln -s /etc/nginx/sites-available/optimized_fba_app.conf /etc/nginx/sites-enabled/ && nginx -t && service nginx restart && service nginx status"
echo.
pause
goto MENU

:DEPLOY_PYTHON
cls
echo ======================================================
echo        部署优化版Python服务器
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 正在部署优化版Python服务器...
echo.
echo 执行命令：ssh root@47.98.248.238 "chmod +x /var/www/fba_app/optimized_run_server.py && pkill -f run_server.py 2>/dev/null || echo '没有运行的服务器进程' && cd /var/www/fba_app && nohup python optimized_run_server.py > server_optimized.log 2>&1 & echo $! > server.pid && ps aux | grep optimized_run_server.py"
echo.
call :SetColor 0A
echo 按任意键继续（或按Ctrl+C取消）...
echo.
call :SetColor 0F
pause >nul
ssh root@47.98.248.238 "chmod +x /var/www/fba_app/optimized_run_server.py && pkill -f run_server.py 2>/dev/null || echo '没有运行的服务器进程' && cd /var/www/fba_app && nohup python optimized_run_server.py > server_optimized.log 2>&1 & echo $! > server.pid && ps aux | grep optimized_run_server.py"
echo.
pause
goto MENU

:CHECK_STATUS
cls
echo ======================================================
echo        检查服务状态
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 正在检查服务状态...
echo.
echo 执行命令：ssh root@47.98.248.238 "service nginx status && echo '---' && ps aux | grep optimized_run_server.py"
echo.
call :SetColor 0A
echo 按任意键继续（或按Ctrl+C取消）...
echo.
call :SetColor 0F
pause >nul
ssh root@47.98.248.238 "service nginx status && echo '---' && ps aux | grep optimized_run_server.py"
echo.
pause
goto MENU

:VIEW_LOGS
cls
echo ======================================================
echo        查看日志文件
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 请选择要查看的日志：
echo [1] Nginx错误日志
echo [2] 优化版服务器日志
set /p log_choice=请输入选项 [1-2]: 

if "!log_choice!"=="1" (
    echo 正在查看Nginx错误日志...
    echo 执行命令：ssh root@47.98.248.238 "tail -n 50 /var/log/nginx/error.log"
    echo.
    call :SetColor 0A
    echo 按任意键继续（或按Ctrl+C取消）...
    echo.
    call :SetColor 0F
    pause >nul
    ssh root@47.98.248.238 "tail -n 50 /var/log/nginx/error.log"
) else if "!log_choice!"=="2" (
    echo 正在查看优化版服务器日志...
    echo 执行命令：ssh root@47.98.248.238 "tail -n 50 /var/www/fba_app/server_optimized.log"
    echo.
    call :SetColor 0A
    echo 按任意键继续（或按Ctrl+C取消）...
    echo.
    call :SetColor 0F
    pause >nul
    ssh root@47.98.248.238 "tail -n 50 /var/www/fba_app/server_optimized.log"
) else (
    call :SetColor 0C
echo 无效的选项！
    call :SetColor 0F
    pause
    goto VIEW_LOGS
)

echo.
pause
goto MENU

:ROLLBACK
cls
echo ======================================================
echo        执行回滚操作
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 警告：此操作将恢复到原始配置！
echo.
echo 执行命令：ssh root@47.98.248.238 "if [ -f '/etc/nginx/sites-available/fba_app.conf.bak' ]; then rm -f /etc/nginx/sites-enabled/*; ln -s /etc/nginx/sites-available/fba_app.conf.bak /etc/nginx/sites-enabled/fba_app.conf; nginx -t && service nginx restart; fi && if [ -f '/var/www/fba_app/run_server.py.bak' ]; then pkill -f optimized_run_server.py; cd /var/www/fba_app; python run_server.py.bak > server.log 2>&1 & echo $! > server.pid; fi && service nginx status && echo '---' && ps aux | grep run_server.py"
echo.
call :SetColor 0C
echo 按任意键继续执行回滚（或按Ctrl+C取消）...
echo.
call :SetColor 0F
pause >nul
ssh root@47.98.248.238 "if [ -f '/etc/nginx/sites-available/fba_app.conf.bak' ]; then rm -f /etc/nginx/sites-enabled/*; ln -s /etc/nginx/sites-available/fba_app.conf.bak /etc/nginx/sites-enabled/fba_app.conf; nginx -t && service nginx restart; fi && if [ -f '/var/www/fba_app/run_server.py.bak' ]; then pkill -f optimized_run_server.py; cd /var/www/fba_app; python run_server.py.bak > server.log 2>&1 & echo $! > server.pid; fi && service nginx status && echo '---' && ps aux | grep run_server.py"
echo.
call :SetColor 0A
echo 回滚操作完成！
echo 请验证网站功能是否正常。
echo.
call :SetColor 0F
pause
goto MENU

:EXIT
cls
echo ======================================================
echo        感谢使用FBA网站性能优化部署工具
call :SetColor 1F
echo ======================================================
echo.
call :SetColor 0F
echo 再见！
echo.
pause
exit

:SetColor
color %1
goto :eof