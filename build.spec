# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None
base = None
if sys.platform == "win32":
    base = "Win32GUI"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("ui", "ui"),
        ("core", "core"),
    ],
    hiddenimports=[
        "core.detector",
        "core.scanner",
        "core.services_manager",
        "core.startup_manager",
        "core.external_disk",
        "core.drivers",
        "core.background_optimizer",
        "core.extreme_tuner",
        "core.ultimate_tweaks",
        "core.toolbox",
        "core.optimizers.cleanup",
        "core.optimizers.network",
        "core.optimizers.disk",
        "core.optimizers.performance",
        "core.optimizers.gaming",
        "core.optimizers.services",
        "core.optimizers.security",
        "core.optimizers.overclock",
        "core.optimizers.developer",
        "core.platforms.windows",
        "core.platforms.linux",
        "core.platforms.macos",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Optinix",
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
    icon=None,
)
