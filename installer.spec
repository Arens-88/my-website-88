# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# 设置工作目录为当前目录
sys.path.append('.')

block_cipher = None

# 查找Python DLL路径
python_dll_path = os.path.join(os.path.dirname(sys.executable), "python3.dll")
python311_dll_path = os.path.join(os.path.dirname(sys.executable), "python311.dll")

datas = [
    ('downloads/FBA费用计算器_美国站.exe', 'downloads'),
    ('downloads/FBA费用计算器_日本站.exe', 'downloads'),
    ('downloads/update_info.json', 'downloads'),
    ('version.json', '.')
]

binaries = []
# 添加Python DLL文件
if os.path.exists(python_dll_path):
    binaries.append((python_dll_path, '.'))
if os.path.exists(python311_dll_path):
    binaries.append((python311_dll_path, '.'))

a = Analysis(['installer.py'],
             pathex=['.'],
             binaries=binaries,
             datas=datas,
             hiddenimports=['winshell', 'win32com.client'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='FBA费用计算器安装程序',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          # 添加程序图标 (可选)
          # icon='your_icon.ico'
          )
