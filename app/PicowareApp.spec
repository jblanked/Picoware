# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Picoware.
#
# Build:
#   cd app/
#   pyinstaller PicowareApp.spec

from pathlib import Path

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=[],
    hiddenimports=[
        "customtkinter",
        "darkdetect",
        "PIL",
        "PIL.Image",
        "serial",
        "serial.tools.list_ports",
        "mpremote",
        "mpremote.main",
        "mpremote.commands",
        "mpremote.transport",
        "mpremote.transport_serial",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Picoware",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Picoware",
)

app = BUNDLE(
    coll,
    name="Picoware.app",
    icon=None,
    bundle_identifier="com.picoware.app",
    version="1.0.0",
    info_plist={
        "NSHighResolutionCapable": True,
    },
)
