# NSKO QUANT · Stage 4 report: trading engine, joined up with the desk

26 Nov 2026 · branch `nsko-quant` · not committed (the coordinator commits).

## In plain English

The trading engine and the desktop app now talk to each other properly. On a fresh computer you can create your
account, unlock the desk, change settings, see your brokers, watch a full paper trade walk through all nine steps on
the Trade Card, approve one by hand, hit the kill switch, release it, use the withdraw helper, roll a strategy back,
and see the go-live checklist. All of that was run for real: the real engine, the real desk, in a browser driven by a
script. **53 of 53 checks passed.** The engine's own tests: **159 passed.**

What it has **not** done: trade on a real Kraken or Alpaca account. There are no API keys in this build machine, so
those two adapters were tested against the exact request shapes their official code uses, not against their servers.

## What was built

### Before this stage (summary of `ENGINE-CORE-NOTES.md`)
The trade flow: scanner (approved strategies, closed bars only) → news blackout → forecast (block-bootstrap fallback,
Kronos when installed) → entry at the live quote → Time Machine (10,000 replays) → size → hard risk gate → debate (veto
only) → bracket order → manage (50 % off at 1R, stop to breakeven) → exit → journal + alert. Auto and Manual (60 s,
default skip). Kill switch from the desk and Telegram. Paper broker with native brackets; Alpaca and Kraken adapters;
Coinbase and IBKR optional; Capital.com, IG, OANDA and MT5 "coming soon". Strategy versions with rollback, signed
strategy packs, live-unlock checklist, withdraw helper.

### Integration work in this stage

**Engine ↔ desk contract (every mismatch in `DESKTOP-NOTES.md` §6 reconciled; full table in `engine/CONTRACT.md`).**
Where the engine was cleaner, the desk changed (`/trading/enable` instead of `/kill {action:"release"}`, `/live/unlock`
instead of a settings write, `/backup/*` instead of `/desk/*`); where the desk's need was real, the engine grew it
(batch settings, JSON backup export, withdraw steps, pause, shutdown, rollback to a chosen version, a new-version
endpoint, broker connect by keychain reference, `?key=` licence check, optional login email, licence at sign-up).
All engine-to-desk shape mapping lives in one file, `app/src/api.ts`.

**Security model kept and tightened.**
- Localhost only. The engine now refuses to start on a non-local address unless `NSQ_ALLOW_NON_LOCAL=1` (set only inside the Docker image).
- Every POST needs `X-NSQ-Client`. CORS allows `tauri://localhost`, `http://tauri.localhost`, `https://tauri.localhost` and `localhost/127.0.0.1` on 5173/4173 only. CORS is now the outermost middleware, so a refused request still tells the desk why.
- Sensitive endpoints need a session token. The stage-3 routers (data, research, Lab, God's Eye) now need a session for every POST; reading stays open on localhost.
- The WebSocket needs `?token=` (a valid session) and a known origin.
- **Kill always works**: `/kill` needs no login, from the desk, the tray, curl or Telegram.
- **Tray without a login**: the engine writes a fresh random secret to `<data_dir>/shell.token` (owner-only) at every start. The Rust shell reads it and sends `X-NSQ-Shell` for pause / resume (`/trading/pause`) and quit (`/engine/shutdown`). A web page cannot read that file.

**Pause** is new: `trading.paused` stops NEW entries only (open trades keep their broker-side stops and are still managed).
The tray, the Settings page and the withdraw helper use it; `/health` and the `engine_health` event report `paused` and `killed`.

**PyInstaller.** `engine/nsko-quant-engine.spec` (one-file, what CI and the Tauri sidecar need) was added and built here:
a 58 MB Linux binary that printed `NSKO QUANT engine 0.2.0` for `--version`, served `/health`, and wrote the tray secret
with mode 0600. The entry accepts `--host`, `--port`, `--version` (and `--watchdog`).

**CI** copied to the repo root: `/.github/workflows/nsko-quant-build.yml` (GitHub only runs root workflows). Changes: the
engine tests run before PyInstaller, PyInstaller is pinned to 6.11.1, the `--version` smoke test is now a hard check,
pull requests also trigger it. **Not run** (no push was made).

**The desk now draws engine data, not demo overlays, in engine mode** (demo mode is unchanged; checked page by page):
- **Trade Card**: built from the real events of the latest plan (scan_hit … exit_done), including the forecast P10–P90 band, Time Machine split, the real risk-gate checks, the bracket and fill, scale-out and the P&L. Skips show the step and reason. Manual shows Approve / Skip with the countdown.
- **Live Desk**: candles from `/data/candles` and `candle` events (the engine now runs a 1-minute candle feed and the Kraken trade stream), real profile POC / VAH / VAL (`profile_update` or `/data/profile`), order-flow bubbles of that market, the latest forecast fan, real positions with their broker-side stop and target lines, the real journal. A chip says SYNTHETIC or REAL and the source.
- **Lab**: variants from `/lab/variants` + `variant_tested`; the fan draws each variant's real equity curve from `/lab/fan` (% return over the test window, after costs); PBO and data source of the last run.
- **Research**: sources, the last summary (with its highlighted terms) and the terms found, from `/research/*` + events.
- **Agent Room**: figure states from `agent_status`, packets and a handoff table from `agent_handoff`.
- **Overview**: engine counts instead of the demo constants.
- **JARVIS**: `POST /jarvis/chat` uses the local model through Ollama when it is running; otherwise it says plainly that the local model is not installed, how to install it, and lists only facts the engine knows (mode, equity, positions, limits).
- **Decisions**: Approve / Skip on a Manual trade goes to the engine.

**Coordinator's extra items, done:**
1. Settings → Alerts: ntfy server and topic; Telegram bot token (stored in the vault / OS keychain, never in settings, never readable back); pairing by a one-time 6-digit code you send to your bot as `/pair 123456` (10 minutes, 5 tries); "Send a test alert". Channel on/off switches are honoured by the engine.
2. The risk gate reads God's Eye risk flags when `godseye.risk_actions = "apply"`: `pause_new` blocks a new entry on that market (risk rule `godseye_flags`), `cut_size` multiplies the size by `godseye.cut_size_factor` (0.5). They can only reduce risk. Settings has the Suggest / Apply choice.
3. The demo Brokers list now matches the engine: Paper connected; Alpaca, Kraken, Coinbase, IBKR "Connect"; Capital.com, IG, OANDA, MT5 "COMING SOON" with their reasons.

**Dev-only trade trigger**: `POST /dev/run-demo-trade`, mounted only with `NSQ_DEV=1` and still needing a session. It
runs the REAL flow and paper broker on seeded synthetic candles with a test signal (flagged `synthetic` everywhere),
then walks the price to 1R and the target so the exit is visible.

## Acceptance checks (master build plan, Stage 4)

| Check | Result | Evidence |
|---|---|---|
| Full flow on paper: **simulator** | ✅ | e2e: two full trades through all nine steps, journal, audit (screens 08–11) |
| Full flow on paper: **Kraken** | ❌ not run against Kraken | no API key here. Signing and AddOrder shape tested against ccxt's reference (`test_adapters.py`); public endpoints probed live in Stage 2/3 |
| Full flow on paper: **Alpaca paper** | ❌ not run against Alpaca | no API key here. Bracket request shape tested against `alpaca-py` (`test_adapters.py`) |
| Bracket orders verified | ✅ paper · ⚠️ real brokers | paper native bracket with OCO legs, fallback path, flaky leg retry, "close if no stop" (`test_execution.py`); e2e shows `native (stop + target at the broker)` |
| Every risk block tested | ✅ | 17 tests in `test_risk.py` (each rule) + 2 new God's Eye flag tests; e2e shows the 12 checks per trade |
| Kill switch | ✅ | e2e: hold 1.5 s → 2 orders cancelled, 1 position closed, locked; release needs the login; tray `/kill` with no login; Telegram `/kill` paired-only in pytest |
| Auto and Manual | ✅ | e2e: Auto trade; Manual waits at the ticket, Approve fills it; pytest: timeout = skip |
| Strategy updates with rollback | ✅ | e2e: roll back v2 → v1, promote to paper, live refused while locked; pytest: queued while a live trade is open, auto-update modes |
| No-look-ahead test | ✅ | `test_flow.py` (forming bar dropped, future bars cannot change signals) + 10 generator cases in `stage3_signals.py` |

## Test results
- Engine: `cd engine && .venv/bin/python -m pytest -q` → **159 passed** (132 before; 27 new in `tests/test_integration.py`, covering every new endpoint, the tray secret, CORS, WS token, stage-3 POST auth, JARVIS with and without Ollama, the dev trade, the CLI flags, God's Eye flags in the gate, Telegram pairing, test alerts).
- Desk: `cd app && npx tsc -b && npx vite build` → passes.
- End to end: `node tools/e2e-stage4.cjs` (real engine on a temp `NSQ_DATA`, `NSQ_DEV=1`, built desk on `vite preview`, headless Chromium) → **53/53 checks**; results in `docs/screenshots/stage-4/results.json`; screenshots 01–24 there (looked at one by one). A separate demo-mode pass over 11 pages showed the DEMO DATA chip everywhere and no page errors (screens 25-*).
- Rust shell: the tray change (shared secret, `/trading/pause`) could **not** be compiled here: `cargo check` was stopped when free disk fell below 600 MB (the container has under 1 GB free). The change is small and was reviewed by hand; CI will compile it.

## What is faked or synthetic
- The e2e trades used the dev trigger: seeded synthetic candles + a test signal. The flow, paper broker, sizing, risk gate, brackets, journal and audit are real.
- Gold candles on the Live Desk are synthetic (no gold broker connected); they are labelled SYNTHETIC. They come from a different generator than the dev trade, so the dev trade's price (≈3,422) does not match the desk's gold chart (≈1,665).
- Forecast = block-bootstrap fallback (Kronos not installed). Debate = rules (Ollama not running). JARVIS = the honest "not installed" answer.
- Strategy Book "key figures" and its equity chart are still the demo drawing (labelled DEMO) even in engine mode.

## What is left
- Run Kraken and Alpaca paper end to end with real keys (Ernest's demo keys, entered in the app, never in chat).
- Run the CI workflow (push to `nsko-quant`), then install on Windows and macOS.
- Compile the Rust shell change (CI does this).
- Wire the Strategy Book's figures and the Knowledge Base page to the engine.
- `/engine/shutdown` under an OS service with `Restart=always`: the service starts the engine again; the tray should stop the service instead (needs a platform helper).
- If the engine runs as an OS service under another user, the tray cannot read `shell.token`: pause from the tray then fails (kill still works).
