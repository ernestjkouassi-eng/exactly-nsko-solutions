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
