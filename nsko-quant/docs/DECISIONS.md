# NSKO QUANT · decisions log

One line per decision: what, and why.

- 26 Nov 2026 · Code lives in the `nsko-solutions` repo under `nsko-quant/`, on branch `nsko-quant` (no separate repo exists yet; this keeps the work safe on GitHub).
- Stage 1 is the React + TypeScript + Vite front end only. The Tauri 2 shell, packaging, keychain and service come in Stage 2 (master prompt section 7), so the Stage 1 app runs in a browser for review.
- No Tailwind: one hand-written `styles.css` driven by the tokens (`src/tokens.ts`), which is less code and matches the dense "mission control" look.
- Motion is Framer Motion for the page change (150 ms out, 250 ms in with an 8 px rise, ease 0.2/0.8/0.2/1). Every live visual is a canvas or three.js loop, and all of them stop under `prefers-reduced-motion`.
- 2D canvas, not PixiJS, for the Lab equity fan (560 lines), the brain sphere (3,000 points), the star field and the order-flow overlay. It measured about 50 fps in headless software rendering, so a GPU laptop should hold 60. PixiJS can be swapped in later if a real machine drops frames.
- three.js + React Three Fiber for the Agent Room and the Stage 1 God's Eye globe. The globe is procedural with demo layers. CesiumJS with free imagery replaces it in Stage 3 (no Cesium ion, no Google 3D Tiles).
- TradingView Lightweight Charts (Apache-2.0) for the Live Desk, with its attribution logo kept on. Order-flow bubbles, zones, the tick-volume profile and the Kronos fan are drawn on an overlay canvas using the chart's own price/time coordinates.
- Demo simulator (`src/demo/sim.ts`) is seeded, so the same demo plays the same way every time, and it emits the section 10 event names (`tick`, `orderflow_bubble`, `ticker_log`, `source_added`, `agent_handoff`, `variant_tested`, `engine_health`, `budget_update`). Stage 2 replaces the source with the engine WebSocket.
- Gold order flow is labelled "tick-volume profile": CFD brokers do not give exchange volume (section 8.1).
- Fonts are bundled locally (@fontsource Inter + JetBrains Mono, OFL), so the desktop app needs no internet for type.
- The brand mark is Ernest's own NSKO "N" symbol from `brand/logo` (with the orange fragment). The lockup SVG text uses Inter; convert it to outlines before print.
- The "THINK BUDGET" shows £ as in the reference; in free/Ollama mode it is compute, not money (Costs page says so). Revisit the label in Stage 2.
- Placeholder: *UK FCA rules on software that trades for others and on financial promotions must be checked with a regulatory lawyer before sale.*
- The master build prompt and the text reference board were pasted in chat (26 Nov 2026). Add both `.md` files to `docs/` as the source of truth. The PDF reference board and the interface / trade-card / order-flow / forecast videos were not provided; Stage 1 follows the text descriptions. Only the God's Eye and alt-data videos were supplied.
- 26 Nov 2026 · Engine: FastAPI + uvicorn on 127.0.0.1:8787 only, SQLite in WAL mode (no DuckDB: nothing needed it yet), APScheduler BackgroundScheduler for jobs.
- Engine: every POST needs an `X-NSQ-Client` header and sensitive endpoints need a session token, so a web page cannot drive the local engine; `/kill` needs no login so it always works.
- Engine: one random data key per desk, wrapped by Argon2id keys from the password and from the recovery code; a password reset never loses encrypted data. The 6-digit PIN only unlocks the screen, never data.
- Engine: licences are `NSQ1.<payload>.<Ed25519 sig>`, checked offline; strategy packs use the same NSKO key with the `NSQPACK1` prefix and install into the Lab only. The private key lives in `tools/keys/` (git-ignored).
- Engine: vault falls back to an AES-GCM file keyed by the signed-in user's data key (or a Docker-secret passphrase on servers) when no OS keychain exists.
- Engine: the risk gate is always on in live, and live limits are clamped to hard caps (2 % per trade, 5 % daily, 10 % weekly, 10 trades, 4 open, 4 % per market) whatever the settings say.
- Engine: the multi-agent debate runs only after the risk gate passes and can only answer take or veto.
- Engine: execution never leaves a position without a broker-side stop; if a stop cannot be placed and verified after 3 idempotent retries, the position is closed.
- Engine: Time Machine and forecast fallback use a block bootstrap (blocks of 8 bars) of the market's own recent bars; when stop and target are both touched in one simulated bar, the stop counts first.
- Engine: brokers whose docs could not be reached from the build machine (Capital.com, IG, OANDA) and MT5 (Windows-only package) ship as "coming soon" with the reason. Alpaca, Kraken, Coinbase (official SDK) and IBKR (ib_async) were verified from live probes and SDK source.
- Engine: Kraken spot has no bracket orders; the stop is always broker-side and the target falls back to engine-side if Kraken refuses a second exit order. Gold on Kraken is the PAXG/USD proxy.
- Engine: Windows service uses NSSM (public domain) rather than WinSW (MIT): simpler to script, no XML.
- Engine: paper account currency is GBP with fixed FX rates in settings until a live FX feed exists.
