# -*- mode: python ; coding: utf-8 -*-
"""MacAPK PyInstaller spec — builds a standalone macOS .app."""

import os
import sys
from pathlib import Path

PROJECT = Path(SPECPATH)
SRC = PROJECT / 'src'
UI = PROJECT / 'ui'

a = Analysis(
    [str(SRC / 'macapk' / '__main__.py')],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (str(UI), 'ui'),
    ],
    hiddenimports=[
        'psutil',
        'macapk',
        'macapk.engine',
        'macapk.collectors',
        'macapk.collectors.cpu',
        'macapk.collectors.gpu',
        'macapk.collectors.ram',
        'macapk.collectors.disk',
        'macapk.collectors.battery',
        'macapk.collectors.network',
        'macapk.collectors.sensors',
        'macapk.collectors.security',
        'macapk.collectors.processes',
        'macapk.storage',
        'macapk.storage.history',
        'macapk.analyzers',
        'macapk.analyzers.diagnoser',
        'macapk.api',
        'macapk.api.server',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2', 'IPython', 'jupyter'],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MacAPK',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='MacAPK',
)

app = BUNDLE(
    coll,
    name='MacAPK.app',
    icon=str(PROJECT / 'assets' / 'icon.icns') if (PROJECT / 'assets' / 'icon.icns').exists() else None,
    bundle_identifier='nl.macapk.app',
    info_plist={
        'CFBundleName': 'MacAPK',
        'CFBundleDisplayName': 'MacAPK — Keuring voor je Mac',
        'CFBundleIdentifier': 'nl.macapk.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'MAPK',
        'LSMinimumSystemVersion': '12.0',
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticTermination': True,
        'NSHumanReadableCopyright': '© 2026 MacAPK',
    },
)