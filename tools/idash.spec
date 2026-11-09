# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent
DIST = ROOT / "dist"

datas = [
    (str(ROOT / "dashboards"), "dashboards"),
    (str(ROOT / "home"), "home"),
    (str(ROOT / "settings"), "settings"),
    (str(ROOT / "studio"), "studio"),
    (str(ROOT / "themes"), "themes"),
    (str(ROOT / "update"), "update"),
    (str(ROOT / "core" / "media_smtc.ps1"), "core"),
    (str(ROOT / "VERSION"), "."),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "requirements.txt"), "."),
    (str(ROOT / "requirements-windows.txt"), "."),
]
helpers = [DIST / "idash-update.exe", DIST / "idash-update"]
for helper in helpers:
    if helper.is_file():
        datas.append((str(helper), "tools"))
        break

hiddenimports = []
binaries = []
try:
    data, bins, hidden = collect_all("acevo")
    datas += data
    binaries += bins
    hiddenimports += hidden
except Exception:
    pass

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "pystray", "PIL", "PIL.ImageDraw", "truck_telemetry",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="idash",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "idash.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="idash",
)
