# NSKO QUANT · Engine core and trading engine (Stage 2 + Stage 4) notes

26 Nov 2026 · branch `nsko-quant` · code in `nsko-quant/engine/nsq` (excluding `research/`, `data/`, `lab/`,
`godseye/`, which another agent owns) · service files in `nsko-quant/deploy/` · licence tool in
`nsko-quant/tools/make-licence/`. Nothing was committed.

## What was built

**Shared contract modules (CONTRACT.md):** `bus.py` (publish/subscribe, thread-safe, ring buffer), `db.py` (SQLite WAL,
dict rows, all core tables), `audit.py` (append-only hash chain + `verify_chain()`; SQLite triggers refuse UPDATE/DELETE),
`settings.py` (get/set with the 9.4 defaults).

**Engine skeleton:** FastAPI app (`python -m nsq` → 127.0.0.1:8787), `/ws` broadcasting `{type, ts, payload}`,
APScheduler jobs (health every 1 s, network check every 10 s, Telegram poll every 5 s, scan each minute, manage every
5 s, daily summary 21:17 UTC), JSON logger with key/token redaction, `GET /health` (uptime, heartbeat, CPU, RAM via
psutil, keep-awake state), `engine_health` event every second. CORS limited to the app's origins; every POST needs an
`X-NSQ-Client` header (blocks drive-by requests from web pages); sensitive endpoints need a session token.

**Account and licence:** Argon2id password hash; a random data key (DEK) wrapped twice (by an Argon2id key from the
password and from the recovery code) encrypts sensitive local data (TOTP secret, vault file) with AES-256-GCM; optional
6-digit PIN (5 tries, then 5-minute lockout; it never unlocks data); optional TOTP (pyotp); recovery code shown once at
sign-up, re-issued after a reset. Offline Ed25519 licences `NSQ1.<payload>.<sig>` with name, email, expiry, tier
Standard|Pro → `valid` / `invalid` / `expired`. Endpoints `/account/create`, `/account/login`, `/licence/check` (+ PIN,
TOTP, recover). `tools/make-licence/make_licence.py` does `keygen`, `sign`, `verify`, `sign-pack`. A keypair was
generated: the public key is in `engine/nsq/licence_key.py`; the private key is at `tools/keys/licence_private.pem`
(git-ignored, confirmed with `git check-ignore`). **Ernest: back that file up offline, or run `keygen --force` on
your own machine to make your own (old licences then stop working).**

**Secrets vault:** OS keychain through `keyring`; when no real backend exists (headless Linux, Docker) an AES-GCM file
keyed by the account data key (or, on a server, by a Docker-secret passphrase). Write-only from the API (names listed,
values never returned). Never in backups, never logged.

**24/7 service:** `deploy/linux` (systemd unit wrapped in `systemd-inhibit`, `Restart=always`, plus a watchdog unit),
`deploy/macos` (launchd `RunAtLoad` + `KeepAlive`, wrapped in `caffeinate -i -s`, plus a watchdog plist),
`deploy/windows/install-service.ps1` (NSSM, public-domain licence; engine calls `SetThreadExecutionState`),
`nsq/watchdog.py` (restarts a stuck engine), reboot recovery (`recovery.py`), internet-drop handling (`connectivity.py`),
Export / Restore my desk (`backup.py`), `deploy/docker` (Dockerfile + compose, published on host 127.0.0.1 only),
`deploy/pyinstaller` spec (built and smoke-tested here: a 149 MB one-folder bundle that serves `/health`).

**Paper broker (default):** spread, slippage and commission per market, native brackets with one-cancels-other legs,
partial closes, gap-through stop fills, idempotent client order IDs, state persisted so a restart picks up where it
left off. Account currency GBP. Failure injection for tests (no native brackets, rejected legs, offline).

**Notifications:** ntfy (topic and server URL from settings, self-hostable, priority high/urgent) and Telegram Bot API
(token in the vault, chat id in settings) for every trade, error, kill switch and the daily summary. Telegram
`/kill` and `/status` work only from the paired chat id; others are refused and audited.

**Demo source:** `nsq/demo.py` emits the same shapes as `app/src/demo/sim.ts` (tick, orderflow_bubble, ticker_log,
source_added, agent_handoff, variant_tested, budget_update) plus a demo trade-card cycle. Every payload has
`"demo": true`. It runs only on the paper broker with no data connected, and stops when a broker is connected.
`engine_health` is always real.

**Trade flow (Stage 4, `nsq/trading/flow.py`):** SCANNER (approved paper/live strategies only; closed bars only) →
NEWS (±15 min of high-impact events from `news.events`, `news.calendar_file` and the shipped calendar in
`nsq.data`) → FORECAST (Kronos if installed, otherwise the "block-bootstrap fallback", 1000 paths, ≥55 % agree)
→ ENTRY (signal from closed bar t, entry at the live quote) → TIME MACHINE (10,000 block-bootstrap replays,
P(target)/P(stop)/P(open), EV after costs > 0) → SIZE (max £ loss ÷ (stop × value per point), rounded down) →
RISK GATE → DEBATE (Ollama at localhost:11434 if up, else rules; veto only) → EXECUTE (bracket, or verified fallback;
idempotent client IDs; closes the position if the stop cannot be placed) → MANAGE (50 % off at 1R, stop to
breakeven, optional ATR trail, end-of-session flatten for intraday) → EXIT → JOURNAL + ALERT. Auto runs straight
through; Manual waits at Execute for `/trade/approve` (60 s, default skip). Kill switch `POST /kill` and Telegram
`/kill`. Strategy versions with rollback, auto-update to paper with "auto"/"ask" promotion, live never changes
mid-trade (queued until flat), signed packs into the Lab only. Live unlock checklist (21 days AND 30 paper trades,
valid licence, real broker with trading on / withdrawals not on, typed phrase) and 50 % size for the first 2 weeks.
Withdraw helper: equity minus margin used, and the broker's own withdrawal page link.

## Test results

```
$ .venv/bin/python -m pytest -q tests
..................................................................       [100%]
66 passed in 1.84s
```

| File | Tests | Covers |
|---|---|---|
| `test_risk.py` | 17 | every risk-gate block (per-trade 1 %, daily 3 % + stop for the day, weekly 6 %, 5 trades/day, 2 open, market exposure, stale data, broker offline, spread too wide, no stop, zero size, kill lock), gate cannot be disabled in live, live hard caps, settings API refusal |
| `test_execution.py` | 13 | native bracket, idempotent retry, fallback path, fallback closes an unprotected position, flaky leg retry, sizing rounding, partial close + OCO, stop slippage, kill switch, `/kill` endpoint + Telegram paired-only, reboot recovery re-places a missing stop, internet drop, withdraw helper (and a scan proving no withdrawal API calls exist) |
| `test_flow.py` | 17 | end-to-end paper trade on synthetic candles through every step to journal + alert, news blackout, unapproved strategy, manual timeout = skip, manual approve, auto, killed flow, NO-LOOK-AHEAD (forming bar dropped, future bars cannot change signals, for both the lab generator and the fallback), entry at the live quote, versions + rollback, live never changes mid-trade, auto-update to paper + ask, signed packs, live unlock checklist + 50 % size, demo shapes + demo flag, `/health` + `/ws`, broker catalogue |
| `test_security.py` | 15 | account create / login / wrong password / weak / duplicate, TOTP, PIN lockout, recovery keeps the data key, endpoints, licence valid / expired / invalid (forged payload, wrong key, garbage), only the public key ships, audit chain tamper detection, audit + log redaction, encrypted vault file, backup round trip without broker keys |
| `test_adapters.py` | 4 | Kraken signature and AddOrder request shape, Alpaca bracket request shape, coming-soon adapters refuse |

## Brokers: real vs coming soon

The build machine could not open any broker documentation site (docs.alpaca.markets, docs.kraken.com,
developer.oanda.com, open-api.capital.com, labs.ig.com all failed DNS through the sandbox proxy). What I could
verify, I verified from live API probes and from official / reference SDK source code downloaded from PyPI.

| Broker | Status | Verified from |
|---|---|---|
| Paper | **ready** (default) | our own simulator |
| Alpaca | **ready** (REST, paper-api by default) | Alpaca's official `alpaca-py` 0.45 source (bracket fields, endpoints) + live probes of paper-api / data.alpaca.markets (auth headers, 401 without keys, public crypto bars). Native brackets for US equities (whole shares); crypto uses the fallback. Withdrawals OFF (trading keys cannot move money). |
| Kraken | **ready** (REST, spot) | live probes of api.kraken.com (Time, AssetPairs, OHLC; `EAPI:Invalid key` on private) + AddOrder / signing as in the open-source ccxt `kraken.py`. No native brackets → fallback; if Kraken refuses a second exit order for lack of free balance, the stop stays broker-side and the target is engine-side. Gold = PAXG/USD proxy. Withdrawal permission is **not detectable** without touching funding endpoints, so the app must tell the user to leave "Withdraw Funds" unticked. |
| Coinbase Advanced | **ready, optional SDK** | Coinbase's official `coinbase-advanced-py` 1.8.4 source (market orders, `trigger_bracket_gtc` exit bracket, `key_permissions` with `can_transfer`). Refuses a key that can transfer. Needs `pip install coinbase-advanced-py`. Not tested against a real account. |
| Interactive Brokers | **ready, optional** | `ib_async` 2.1.0 source (`bracketOrder`, `placeOrder`, `positions`, `openTrades`). Needs IB Gateway/TWS running (default port 4002 = paper) and `pip install ib_async`. Not tested against a real Gateway. |
| Capital.com | coming soon | docs host blocked; endpoints not verified, so not shipped |
| IG | coming soon | docs host blocked; endpoints not verified |
| OANDA | coming soon | docs host blocked; endpoints not verified |
| MT5 | coming soon | the `MetaTrader5` package is Windows-only (no Linux wheel), could not be installed or read |
| CMC Markets | not supported | no retail bot API |

## What was faked, assumed or not verifiable

- **No real-money or real-account order was placed** on any broker. Alpaca/Kraken request shapes are tested against
  mocked HTTP; the public endpoints were probed live.
- **Paper costs are approximations** (`brokers/base.py: MARKETS`), not quotes from any broker. GBP conversion uses fixed
  rates in settings (`fx.USD` = 0.79 by default); there is no live FX feed yet.
- **Paper margin** is a flat 5 % of notional, for the withdraw helper only.
- **Kronos** is not installed here, so every forecast in tests used the block-bootstrap fallback (named as such). The
  Kronos call follows the repo's README-level API and is wrapped so any failure falls back.
- **Ollama** is not running here, so the debate used the deterministic rules. The LLM path is untested.
- **Keep-awake**: Windows `SetThreadExecutionState` and macOS `caffeinate` paths were not run (Linux build machine);
  on Linux the container has no logind, so `systemd-inhibit` reports "unavailable" (the engine says so in /health).
- **Session end** for the Time Machine and intraday flatten uses fixed UTC times (20:00 US equities, 21:00 FX/metals),
  ignoring daylight-saving shifts.
- The **e2e test** uses a test signal generator (a long on the last closed bar) so the flow is deterministic; the
  lab's real generators are exercised by the no-look-ahead test.
- **ntfy / Telegram** sends were not made from here (no topic or token); the code paths, pairing and `/kill` handling are
  tested offline.
- Service files (systemd, launchd, NSSM, Docker) were written but not installed on a real machine here; Docker was not
  available to build the image. The PyInstaller bundle was built and served `/health` on Linux.
- The app (`app/`) still uses its own simulator; switching `src/store.ts` to `ws://127.0.0.1:8787/ws` is a front-end
  job (not touched, as instructed).
