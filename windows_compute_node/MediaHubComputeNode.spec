# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


WINDOWS_NODE = Path(SPECPATH).resolve()
REPO_ROOT = WINDOWS_NODE.parent
ENTRYPOINT = WINDOWS_NODE / "main.py"


if not ENTRYPOINT.is_file():
    raise RuntimeError(
        f"Windows Compute Node entrypoint fehlt: {ENTRYPOINT}"
    )


a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[
        (
            str(WINDOWS_NODE / "assets" / "MediaHub-Compute-Node.ico"),
            "assets",
        ),
    ],
    hiddenimports=[
        "pystray._win32",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "windows_compute_node.plugin_sources",
    ],
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
    name="MediaHub-Compute-Node",
    icon=str(
        WINDOWS_NODE
        / "assets"
        / "MediaHub-Compute-Node.ico"
    ),
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
)
