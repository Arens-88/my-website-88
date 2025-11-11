@echo off
cd d:\FBA\fba\FBA
echo 正在更新下载文件...
if exist "downloads\FBA费用计算器v1.2.4.exe" (
    copy "downloads\FBA费用计算器v1.2.4.exe" "downloads\FBA费用计算器.exe" /Y
    echo 文件复制完成！
) else (
    echo 源文件不存在，请检查路径！
)
dir downloads\*.exe
echo 更新完成！
pause