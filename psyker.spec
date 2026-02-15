# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


try:
    project_root = Path(__file__).resolve().parent
except NameError:
    # When the spec is executed in an environment where __file__ is not set,
    # fall back to the current working directory (expected to be repo root).
    project_root = Path.cwd()
icon_path = project_root / "vscode-extension" / "icons" / "logo_icon.ico"
if not icon_path.exists():
    icon_path = project_root / "icons" / "logo_icon.ico"

datas = []
# Bundle Grammar Context (valid/invalid examples) for users; md contexts excluded (internal specs)
for source, target in [("Grammar Context", "Grammar Context"), ("assets", "assets")]:
    source_path = project_root / source
    if source_path.exists():
        datas.append((str(source_path), target))


a = Analysis(
    ["psyker_frozen_entry.py"],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
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
    [],
    exclude_binaries=True,
    name="Psyker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Psyker",
)
