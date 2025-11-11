import json
with open('version.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
data['download_url'] = 'downloads/FBA费用计算器v1.2.4.exe'
data['size'] = '10.7 MB'
with open('version.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
print('版本信息更新成功！')