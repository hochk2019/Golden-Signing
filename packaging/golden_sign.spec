# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec — Golden Sign 1.0.0."""

from pathlib import Path

# SPECPATH = packaging/; repository root is its parent
root = Path(SPECPATH).resolve().parent  # noqa: F821 — provided by PyInstaller
icon = root / "assets" / "branding" / "golden-app-icon.ico"

a = Analysis(
    [str(root / "src" / "golden_signing" / "app" / "bootstrap.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
        (str(root / "assets" / "branding"), "assets/branding"),
        (str(root / "assets" / "ui"), "assets/ui"),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "golden_signing",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GoldenSign",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon) if icon.is_file() else None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GoldenSign",
)
