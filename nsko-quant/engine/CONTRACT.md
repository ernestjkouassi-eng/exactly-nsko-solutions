# Engine contract (shared by every engine module)

Package: `engine/nsq` (Python 3.11+). Run: `python -m nsq` → FastAPI on 127.0.0.1:8787 (localhost only).

- `nsq/bus.py`: `publish(type: str, payload: dict)` (sync, thread-safe) and `subscribe(fn)`. The WebSocket `/ws` broadcasts every event as `{"type", "ts" (ms), "payload"}`.
  Event types (section 10, use these names exactly): tick, candle, orderflow_bubble, profile_update, ticker_log, agent_status, agent_handoff, source_added, summary_done, term_found, recipe_created, variant_tested, backtest_done, strategy_status, decision_needed, scan_hit, news_hit, forecast_done, entry_state, timemachine_progress, timemachine_done, size_calc, risk_check, order_sent, order_filled, position_update, exit_done, alert, gods_eye_event, market_impact, kill_switch, engine_health, budget_update.
  `ticker_log` payload: `{"verb": SEARCH|READ|SAVE|REJECT|TERM|SUMMARISE|PAUSE|BUDGET|TRADE|TEST|RISK, "msg": str}`.
  `variant_tested` payload: `{id, recipe, market, tf, sharpeIS, sharpeOOS, trades, win, rr, dd, outcome: clear|sieve|failed, why, seed}`.
- `nsq/db.py`: `conn()` returns a sqlite3 connection (WAL, row factory dict) to `<data_dir>/nsko.db`; `data_dir()` = `$NSQ_DATA` or the OS app-data folder `NSKO QUANT`. Each module creates its own tables with `CREATE TABLE IF NOT EXISTS` in an `ensure()` function.
  Core tables: sources, summaries, terms, recipes, variants, backtests, strategies, strategy_versions, signals, trade_plans, orders, fills, positions, risk_events, alerts, audit_log, settings.
- `nsq/audit.py`: `audit(actor, action, detail: dict)`, an append-only, hash-chained log.
- **Recipe** (JSON, stored in `recipes.json_rules`):
  `{"id","name","market":"XAU/USD","timeframe":"15m","idea_type":"Orderflow","entry":{...},"stop":{"type":"atr|swing|level","mult":1.0},"target":{"type":"r|level","r":1.6},"filters":{"session":["london","ny"],"news_blackout_min":15},"params":{...}}`.
- **Signals:** `nsq.lab.signals.generate(recipe: dict, candles: pandas.DataFrame[open,high,low,close,volume, index=UTC datetime]) -> list[dict]`.
  Each dict is `{"time","side":"buy|sell","entry","stop","target","reason"}`. It uses **closed bars only**, so a signal at bar t uses data up to and including bar t, never t+1.
- **Candles:** `nsq.data.candles.get(market, timeframe, start, end) -> DataFrame`. Sources are the connected broker, public exchange history or cached CSV. If nothing is available, it falls back to a seeded synthetic series that is clearly flagged `synthetic=True` in `df.attrs`.
- **Settings:** `nsq.settings.get(key, default)` / `set(key, value)`, stored in the settings table.

## HTTP contract with the desk (Stage 4 integration, 26 Nov 2026)

The desk's `app/src/api.ts` maps every engine answer into its own shapes in one place. Security rules: localhost only;
every POST carries `X-NSQ-Client`; sensitive calls carry `Authorization: Bearer <session token>`; `/ws?token=<session token>`.

| Desk action | Engine endpoint | Auth |
|---|---|---|
| health, tray colour | `GET /health` → also `paused`, `killed`, `account_exists`, `trade_mode` | none |
| create account | `POST /account/create {email, password, name, pin?, licence_key?}` (an invalid / expired licence is refused) | none |
| login | `POST /account/login {email?, password, totp?}` (email optional: one account per desk) | none |
| licence check | `GET /licence/check?key=` (checks, never saves) | none |
| 2FA | `POST /account/totp/begin` → `{secret, otpauth_uri}`, `/account/totp/confirm {code}` | session |
| kill switch | `POST /kill {reason, source}` | **none, always works** |
| re-enable | `POST /trading/enable` | session |
| pause / resume new trades | `POST /trading/pause {paused}` | session **or** tray secret `X-NSQ-Shell` |
| quit engine (tray) | `POST /engine/shutdown` | session or tray secret |
| approve / skip (Manual) | `POST /trade/approve {plan_id, decision}` | session |
| settings | `GET /settings`; `POST /settings {key, value}` or `{values: {...}}` (all-or-nothing) | session |
| desk backup | `POST /backup/export {passphrase, format: "json"}` → `{filename, data_b64}`; `/backup/restore` | session |
| brokers | `GET /brokers`; `POST /brokers/{name}/connect {environment, keychain_service, keychain_account \| api_key, api_secret}` | session |
| withdraw helper | `GET /withdraw/helper`; `POST /withdraw/helper {action: pause\|close_positions\|rescale\|resume}` | session |
| paper & live | `GET /live/checklist` (+ `phrase`, `paper`); `POST /live/unlock {phrase}` | session |
| strategy book | `GET /strategies?include=versions`; `POST /strategies/{id}/promote {to}`; `/rollback {version?}`; `POST /strategies/{id}/versions {rules, note}` | session |
| alerts set-up | `POST /vault/telegram.bot_token {value}`; `POST /telegram/pair/begin` → code for `/pair <code>`; `POST /notify/test` | session |
| JARVIS | `POST /jarvis/chat {message, history}` (Ollama if running, else an honest "not installed" + facts) | session |
| Lab / research / data / God's Eye | the stage-3 routers: GET open on localhost, **every POST needs a session** | session for POST |
| dev only (`NSQ_DEV=1`) | `POST /dev/run-demo-trade`, `GET /dev/demo-trade` | session |

The tray's shared secret is `<data_dir>/shell.token`, written fresh at every engine start with owner-only permissions.
Trade-flow skips now also send `ticker_log {verb: REJECT, plan_id, step, why}`; `decision_needed` for a trade carries `plan_id`.
