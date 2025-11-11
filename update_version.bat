@echo off
echo 正在更新版本信息...
echo {
> version.json.new
echo     "version": "1.2.4",
>> version.json.new
echo     "build": "20251101001",
>> version.json.new
echo     "release_date": "2025-11-01",
>> version.json.new
echo     "update_date": "2025-11-01",
>> version.json.new
echo     "download_url": "downloads/FBA费用计算器v1.2.4.exe",
>> version.json.new
echo     "size": "10.7 MB",
>> version.json.new
echo     "md5": "b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6"
>> version.json.new
echo }
>> version.json.new

move /y version.json.new version.json > nul
echo 版本信息更新完成！
type version.json