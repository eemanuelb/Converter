# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path


python_root = Path(sys.base_prefix)
dlls_dir = python_root / 'DLLs'
tcl_dir = python_root / 'tcl'


a = Analysis(
    ['Converter.py'],
    pathex=[],
    binaries=[
        (str(dlls_dir / '_tkinter.pyd'), '.'),
        (str(dlls_dir / 'tcl86t.dll'), '.'),
        (str(dlls_dir / 'tk86t.dll'), '.'),
    ],
    datas=[
        (str(python_root / 'Lib' / 'tkinter'), 'tkinter'),
        (str(tcl_dir / 'tcl8.6'), 'tcl/tcl8.6'),
        (str(tcl_dir / 'tk8.6'), 'tcl/tk8.6'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_tkinter_runtime_hook.py'],
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
    name='Converter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
