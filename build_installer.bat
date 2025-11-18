@echo off

echo 开始打包FBA费用计算器安装程序...
echo 当前正在使用修复后的installer.py

rem 先确保dist目录存在
mkdir -p dist

rem 使用PyInstaller打包installer.py
python -m PyInstaller installer.spec
if %errorlevel% neq 0 (
    echo 安装程序打包失败！
    pause
    exit /b %errorlevel%
)

echo 安装程序打包成功！
echo 可执行文件已生成在 dist\FBA费用计算器安装程序.exe
echo.  
echo 请将生成的安装程序复制到网站下载页面的对应位置

pause