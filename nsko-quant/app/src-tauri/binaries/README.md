Engine sidecar binaries go here, named `nsko-quant-engine-<target-triple>` (`.exe` on Windows).
CI builds them with PyInstaller from `nsko-quant/engine/nsko-quant-engine.spec`.
For a local shell-only build, `npm run engine:stub` writes a placeholder that exits at once.
