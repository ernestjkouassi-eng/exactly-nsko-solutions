"""`python -m nsq` -> the engine on 127.0.0.1:8787 (localhost only).

Flags (also used by the PyInstaller build and the Tauri sidecar): --host, --port, --log-level, --version.
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> None:
    from . import __version__
    ap = argparse.ArgumentParser(prog="nsko-quant-engine", description="NSKO QUANT engine")
    ap.add_argument("--port", type=int, default=int(os.environ.get("NSQ_PORT", 8787)))
    ap.add_argument("--host", default=os.environ.get("NSQ_HOST", "127.0.0.1"),
                    help="keep 127.0.0.1; the Docker route sets 0.0.0.0 inside the container only")
    ap.add_argument("--log-level", default="INFO")
    ap.add_argument("--version", action="version", version=f"NSKO QUANT engine {__version__}")
    a = ap.parse_args(argv)
    if a.host not in ("127.0.0.1", "localhost", "::1") and os.environ.get("NSQ_ALLOW_NON_LOCAL") != "1":
        print(f"Refusing to listen on {a.host}: the engine is localhost-only. "
              "(Docker sets NSQ_ALLOW_NON_LOCAL=1 inside the container.)", file=sys.stderr)
        sys.exit(2)
    from . import log
    from .db import data_dir
    log.setup(a.log_level, str(data_dir() / "engine.log"))
    import uvicorn
    from .app import app
    uvicorn.run(app, host=a.host, port=a.port, log_level=a.log_level.lower(), access_log=False, ws="websockets")


if __name__ == "__main__":
    main()
