# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ui', 'ui'),
        ('config', 'config'),
        ('core', 'core'),
    ],
    hiddenimports=[
        'flask', 'webview', 'psutil',
        'core', 'core.detector', 'core.scanner',
        'core.optimizers', 'core.optimizers.cleanup',
        'core.optimizers.network', 'core.optimizers.disk',
        'core.optimizers.performance', 'core.optimizers.gaming',
        'core.optimizers.security', 'core.optimizers.developer',
        'core.optimizers.services', 'core.optimizers.overclock',
        'core.platforms', 'core.platforms.windows',
        'core.platforms.macos', 'core.platforms.linux',
        'app'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PC Optimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PC Optimizer'
)
