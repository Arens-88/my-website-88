@echo off

rem 打包两个站点的FBA费用计算器

echo 开始打包美国站FBA费用计算器...
python -m PyInstaller fba_gui.spec
if %errorlevel% neq 0 (
    echo 美国站打包失败！
    pause
    exit /b %errorlevel%
)

echo 美国站打包成功！
echo 开始打包日本站FBA费用计算器...
python -m PyInstaller FBA_gui_jp.spec
if %errorlevel% neq 0 (
    echo 日本站打包失败！
    pause
    exit /b %errorlevel%
)

echo 日本站打包成功！
echo 正在复制生成的可执行文件到指定位置...

rem 创建输出目录
mkdir -p dist/all

rem 复制可执行文件
copy dist\FBA费用计算器.exe dist\all\FBA费用计算器_美国站.exe
copy dist\FBA费用计算器_日本站.exe dist\all\

echo 打包完成！可执行文件已复制到 dist/all 目录
pause