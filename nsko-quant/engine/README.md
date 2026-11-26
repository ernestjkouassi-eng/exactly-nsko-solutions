# NSKO QUANT engine · by NSKO Solutions

The local background engine. It runs 24/7 on the client's own computer, trades in the client's own broker
account, and talks to the desktop app over `http://127.0.0.1:8787` and the WebSocket `ws://127.0.0.1:8787/ws`.

**Paper trading is the default.** The engine has **no withdrawal code**. The risk gate **cannot be switched
off in live**. When no data or broker is connected, a DEMO source emits the same events as the app's
simulator, and every demo payload carries `"demo": true`.

## Run it

```bash
cd nsko-quant/engine
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m nsq                 # engine on 127.0.0.1:8787
.venv/bin/python -m pytest -q tests     # the test suite
```

Data lives in `$NSQ_DATA`, or the OS app-data folder `NSKO QUANT`
(Windows `%APPDATA%`, macOS `~/Library/Application Support`, Linux `~/.local/share`).

## What is where

| Module | What it does |
|---|---|
| `nsq/bus.py` | `publish(type, payload)` / `subscribe(fn)`; `/ws` broadcasts `{type, ts, payload}` |
| `nsq/db.py` | SQLite (WAL), core tables; `conn()`, `data_dir()` |
| `nsq/audit.py` | append-only, hash-chained `audit_log`; `audit()`, `verify_chain()` |
| `nsq/settings.py` | `get(key, default)` / `set(key, value)` with the 9.4 defaults |
| `nsq/log.py` | JSON logs; every line passes through key/token redaction |
| `nsq/app.py`, `__main__.py` | FastAPI + `/ws`; `python -m nsq` |
| `nsq/engine.py`, `health.py`, `watchdog.py` | APScheduler jobs, `engine_health` every second, keep-awake, watchdog |
| `nsq/account.py`, `crypto.py`, `licence.py`, `vault.py` | Argon2id account, PIN, TOTP, recovery code, AES-GCM, Ed25519 licences, keychain vault |
| `nsq/connectivity.py`, `recovery.py`, `backup.py` | internet-drop handling, reboot reconcile, Export / Restore my desk |
| `nsq/notify.py` | ntfy + Telegram (and the Telegram `/kill` command, paired chat only) |
| `nsq/demo.py` | DEMO event source |
| `nsq/brokers/` | `BrokerAdapter`, `PaperBroker` (default), Alpaca, Kraken, Coinbase, IBKR; coming-soon stubs |
| `nsq/trading/` | the trade flow: news, forecast, Time Machine, sizing, risk gate, debate, execute, manage, strategies, live unlock, kill switch, withdraw helper |

## Main endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | uptime, last heartbeat, CPU, RAM, mode, broker, online, locked |
| WS | `/ws` | every bus event |
| POST | `/account/create`, `/account/login`, `/account/recover` | create returns the recovery code once |
| POST | `/account/pin`, `/account/pin/verify`, `/account/totp/begin`, `/account/totp/confirm` | |
| GET/POST | `/licence/check` | `valid` / `invalid` / `expired` |
| POST | `/kill` | cancel all, close all, lock. No login needed (safety) |
| POST | `/trading/enable`, `/trade/approve` | `/trade/approve {plan_id, decision: approve|skip}` |
| GET/POST | `/live/checklist`, `/live/unlock` | unlock needs the phrase "I understand I can lose money" |
| GET/POST | `/brokers`, `/brokers/connect`, `/brokers/permissions` | keys go straight to the vault |
| GET | `/withdraw/helper` | free amount + the broker's own withdrawal page. No money moves |
| POST | `/backup/export`, `/backup/restore` | encrypted desk file; never broker keys |
| GET | `/audit`, `/audit/verify`, `/risk/events`, `/journal`, `/strategies` | |

Every POST needs the header `X-NSQ-Client` (blocks drive-by requests from web pages). Sensitive endpoints
also need `Authorization: Bearer <token>` from `/account/login`.

## 24/7 service

See `../deploy/`: systemd (Linux), launchd (macOS), NSSM (Windows), Docker, and the PyInstaller spec.
