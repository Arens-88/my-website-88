# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['fba_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='win64',  # 指定64位架构
    codesign_identity=None,
    entitlements_file=None,
    # 添加Windows版本兼容性设置
    version='1.2.4.0',
    company_name='Jerry Tom',
    product_name='FBA费用计算器',
    copyright='© 2025 Jerry Tom',
)
