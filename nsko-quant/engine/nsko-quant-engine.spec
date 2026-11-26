# PyInstaller spec: ONE-FILE build of the engine, used by CI and shipped as the Tauri sidecar
# (Tauri's externalBin needs a single executable: app/src-tauri/binaries/nsko-quant-engine-<target-triple>).
# Build from nsko-quant/engine with the venv active:
#   pip install pyinstaller==6.11.1
#   pyinstaller --noconfirm --clean --distpath dist nsko-quant-engine.spec
# Output: dist/nsko-quant-engine (dist/nsko-quant-engine.exe on Windows).
# Flags: --host 127.0.0.1 --port 8787 (what the shell passes), --version (CI smoke test), --watchdog.
# The one-folder variant for the OS services stays in ../deploy/pyinstaller/nsko-quant-engine.spec.
# PyInstaller is GPL-2.0 with the bootloader exception, so the output may be shipped.
# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_submodules

ENGINE = os.path.abspath(SPECPATH)                       # SPECPATH = this file's folder (nsko-quant/engine)
ENTRY = os.path.join(ENGINE, "..", "deploy", "pyinstaller", "entry.py")

hidden = (collect_submodules("nsq") + collect_submodules("uvicorn") + collect_submodules("keyring.backends")
          + ["argon2", "_argon2_cffi_bindings", "apscheduler.triggers.cron", "apscheduler.triggers.interval", "websockets"])

a = Analysis(
    [os.path.abspath(ENTRY)],
    pathex=[ENGINE],
    binaries=[],
    datas=[(os.path.join(ENGINE, "nsq", "data", "econ_calendar.json"), "nsq/data")],
    hiddenimports=hidden,
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="nsko-quant-engine", console=True, upx=False,
          strip=False, runtime_tmpdir=None)
