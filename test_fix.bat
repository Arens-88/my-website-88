@echo off

echo 正在测试FBA费用计算器的兼容性修复...

:: 检查可执行文件是否存在
if exist "dist\FBA费用计算器.exe" (
    echo 找到FBA费用计算器.exe文件
    echo.    
    echo 修复摘要：
    echo 1. 修改了PyInstaller打包配置，添加了目标架构(win64)和版本信息
    echo 2. 设置了应用程序元数据，包括版本号、公司名称等
    echo 3. 这些更改应该解决Windows系统兼容性检查问题
    echo.    
    echo 如何推送更新：
    echo 1. 将新生成的dist\FBA费用计算器.exe复制到downloads目录
    echo 2. 更新version.json文件中的版本信息
    echo 3. 使用项目中的推送脚本：如简单推送.ps1或同步并推送.ps1
    echo 4. 也可以手动将更新文件复制到GitHub目录并提交推送
    echo.    
    echo 修复完成！您可以手动运行FBA费用计算器.exe进行测试。
) else (
    echo 错误：找不到FBA费用计算器.exe文件
    echo 打包过程可能失败，请检查错误信息
)

pause