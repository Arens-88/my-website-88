# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# 获取Python DLL路径
sys_base = os.path.dirname(sys.executable)

a = Analysis(
    ['fba_gui.py'],
    pathex=['.'],
    binaries=[
        (os.path.join(sys_base, 'python3.dll'), '.'),
        (os.path.join(sys_base, 'python311.dll'), '.'),
    ],
    datas=[
        ('settings.json', '.'),
        ('feedback.json', '.'),
        ('images/', 'images/'),
        ('feedback/', 'feedback/'),
    ],
    hiddenimports=[
        'tkinter',
        'json',
        'os',
        'sys',
        'datetime',
        'math',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FBA费用计算器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir='.',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='win64',  # 指定64位架构
    codesign_identity=None,
    entitlements_file=None,
    # 添加Windows版本兼容性设置
    version_file=None,
    # 设置程序图标
    icon=None,
    company_name='Jerry Tom',
    product_name='FBA费用计算器',
    copyright='© 2025 Jerry Tom',
)
