"""`python -m nsq` -> the engine on 127.0.0.1:8787 (localhost only)."""
from __future__ import annotations

import argparse
import os


def main() -> None:
    ap = argparse.ArgumentParser(prog="nsq", description="NSKO QUANT engine")
    ap.add_argument("--port", type=int, default=int(os.environ.get("NSQ_PORT", 8787)))
    ap.add_argument("--host", default=os.environ.get("NSQ_HOST", "127.0.0.1"),
                    help="keep 127.0.0.1; the Docker route sets 0.0.0.0 inside the container only")
    ap.add_argument("--log-level", default="INFO")
    a = ap.parse_args()
    from . import log
    from .db import data_dir
    log.setup(a.log_level, str(data_dir() / "engine.log"))
    import uvicorn
    from .app import app
    uvicorn.run(app, host=a.host, port=a.port, log_level=a.log_level.lower(), access_log=False, ws="websockets")


if __name__ == "__main__":
    main()
