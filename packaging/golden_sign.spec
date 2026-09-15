# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec — Golden Sign (slim Widgets-only build)."""

from pathlib import Path

# SPECPATH = packaging/; repository root is its parent
root = Path(SPECPATH).resolve().parent  # noqa: F821 — provided by PyInstaller
icon = root / "assets" / "branding" / "gsign" / "golden-signing.ico"
if not icon.is_file():
    icon = root / "assets" / "branding" / "golden-app-icon.ico"

# Drop unused Qt / Python stacks (Widgets app: Core+Gui+Widgets only).
_EXCLUDES = [
    "tkinter",
    "unittest",
    "test",
    # Qt frameworks not used
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtConcurrent",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtHttpServer",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtXml",
    "PySide6.QtXmlPatterns",
    # Python stdlib / third-party not needed
    # NOTE: do NOT exclude asyncio/email — pyHanko (pdf/content) imports them.
    "pydoc",
    "pydoc_data",
    "http.server",
    "xmlrpc",
    "setuptools",
    "pkg_resources",
    "pip",
    "numpy",
    "matplotlib",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "hypothesis",
]

a = Analysis(
    [str(root / "src" / "golden_signing" / "app" / "bootstrap.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
        (str(root / "assets" / "branding" / "golden-mark-ui.png"), "assets/branding"),
        (str(root / "assets" / "branding" / "golden-mark.png"), "assets/branding"),
        (str(root / "assets" / "branding" / "golden-app-icon.ico"), "assets/branding"),
        (
            str(root / "assets" / "branding" / "gsign" / "golden-signing.ico"),
            "assets/branding/gsign",
        ),
        (
            str(root / "assets" / "branding" / "gsign" / "golden-signing-256.png"),
            "assets/branding/gsign",
        ),
        (str(root / "assets" / "ui"), "assets/ui"),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "golden_signing",
    ],
    hookspath=[],
    hooksconfig={
        "PySide6": {
            # Keep only what Widgets needs; avoid pulling Quick/WebEngine plugins.
            "excluded_plugins": [
                "platforms/direct2d",
            ],
        },
    },
    runtime_hooks=[],
    excludes=_EXCLUDES,
    noarchive=False,
)

# PyInstaller's PySide6 hook still ships unused Qt DLLs — strip after analysis.
_DROP_BIN = (
    "Qt6Quick",
    "Qt6Qml",
    "Qt6Pdf",
    "Qt6OpenGL",
    "Qt6Network",
    "Qt6VirtualKeyboard",
    "Qt6Concurrent",
    "Qt6DBus",
    "QtNetwork.pyd",
    "opengl32sw",  # 20MB software GL; Widgets uses raster/D3D on Win
)


def _keep_bin(entry) -> bool:  # noqa: ANN001
    dest = str(entry[0]).replace("\\", "/")
    name = dest.rsplit("/", 1)[-1]
    return not any(d in name for d in _DROP_BIN)


a.binaries = [e for e in a.binaries if _keep_bin(e)]

# Drop Qt translations / unused plugin folders from datas
_DROP_DATA = (
    "/translations/",
    "/PySide6/Qt/translations",
    "/qml/",
    "/Qt/qml",
    "/tzdata/zoneinfo/",
)


def _keep_data(entry) -> bool:  # noqa: ANN001
    dest = str(entry[0]).replace("\\", "/")
    return not any(d in dest for d in _DROP_DATA)


a.datas = [e for e in a.datas if _keep_data(e)]

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
