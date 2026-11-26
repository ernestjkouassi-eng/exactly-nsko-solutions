# PyInstaller spec: one-folder build of the engine (free, GPL with the bootloader exception, so the
# output can be shipped). Build from nsko-quant/engine with the venv active:
#   pip install pyinstaller==6.11.1
#   pyinstaller ../deploy/pyinstaller/nsko-quant-engine.spec --noconfirm
# Output: dist/nsko-quant-engine/ (the Tauri app ships this folder as a sidecar).
# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_submodules

ENGINE = os.path.abspath(os.path.join(SPECPATH, "..", "..", "engine"))  # SPECPATH = this file's folder

hidden = (collect_submodules("nsq") + collect_submodules("uvicorn") + collect_submodules("keyring.backends")
          + ["argon2", "argon2._ffi", "apscheduler.triggers.cron", "apscheduler.triggers.interval", "websockets"])

a = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    pathex=[ENGINE],
    binaries=[],
    datas=[(os.path.join(ENGINE, "nsq", "data", "econ_calendar.json"), "nsq/data")],
    hiddenimports=hidden,
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="nsko-quant-engine", console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="nsko-quant-engine")
