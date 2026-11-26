# NSKO QUANT · Stage 3 report: data, research, Lab, Knowledge Base, God's Eye

26 Nov 2026 · branch `nsko-quant` · built from `docs/STAGE-3-NOTES.md` plus the Stage 4 integration · not committed.

## In plain English

The engine can fetch real bitcoin and ether prices and live trades from Kraken, read research from GitHub and arXiv,
turn ideas into strategy recipes, test each recipe ten ways against a strict pass mark (with costs and overfitting
checks), keep a Knowledge Base of trading terms, and watch flights, earthquakes, weather, launches and satellites for
events that can move markets. God's Eye never places a trade. Anything made up is labelled `synthetic`.

In this stage's integration the desk started showing it: the Lab's equity fan now draws the real equity curve of each
tested variant, the Research page shows the real sources, summaries and terms, and the Agent Room moves on the real
handoffs. All of this was seen on screen against the real engine (screens 21–23 in `docs/screenshots/stage-4/`).

## What was built (summary of `STAGE-3-NOTES.md`)
- **`nsq/data`**: `candles.get` (broker → CSV cache → Kraken public OHLC → seeded synthetic, flagged), Kraken trade backfill, closed-bar resampling; GARCH synthetic data; order flow from the Kraken WS v2 trade stream (bubbles, profile, delta); gold as a tick-volume profile (labelled); news headlines only (GDELT, RSS with robots.txt and no DTDs, economic calendar, SEC EDGAR, House PTRs off by default).
- **`nsq/research`**: the JARVIS team (SCOUT, READER, WATCHER, SUMMARISER 1–3, TERM-CHECKER, RECIPE-MAKER); Ollama when running, otherwise a deterministic offline summariser; daily "think" budget; every step emits its event.
- **`nsq/lab`**: four signal generators including NSKO-OF-1, closed bars only; backtester (next-bar fills, stop-first, gaps, costs, funding); walk-forward; the bar (OOS Sharpe 1.40, 30 trades, 20 % DD, stability, PBO, IS→OOS decline, beats random); Monte Carlo; 10 seeded variants; seed pack of 5 strategies. Only real-data results can create a strategy.
- **Knowledge Base**: 12 concepts with detectors that report the bar where a pattern is confirmed, a 6-step lifecycle and the user's verdict.
- **`nsq/godseye`**: 7 layers with attributions and on/off flags; MARKET IMPACT rules (Hormuz tankers, military surge, M6+ quake near mines/ports, crop weather, NDVI, EIA); Crop Watch over Sentinel-2 scene metadata; Oil Storage (EIA, own key); Car Counts placeholder.

### Added during the Stage 4 integration
- Every state-changing POST of these four routers now needs a signed-in session (reading stays open on localhost).
- The engine runs a 1-minute `candle` feed for `data.feeds` (XAU/USD, BTC/USD) and the Kraken trade stream for crypto while it is up.
- The desk's Lab, Research, Agent Room and Live Desk read these events and endpoints in engine mode; `gods_eye_event` layer batches (`features: [...]`) are expanded into globe points.
- The risk gate now honours God's Eye `cut_size` / `pause_new` flags when the user chose "Apply" (see the Stage 4 report).

## Acceptance checks (master build plan, Stage 3)

| Check | Result | Evidence / honest note |
|---|---|---|
| The research pipeline runs on Ollama | ❌ not verified | **Ollama is not installed in this build machine.** Every round here used the offline summariser (shown as "offline" on the Research page). The Ollama path is written to the documented `/api/generate` API and its answers are validated, but it has never run. |
| The Lab tests real recipes and fills the fan | ✅ | e2e: VWAP-Rev-BTC on real Kraken 15-minute data (`kraken+cache`, not synthetic), 10 variants, all failed the bar ("too few trades": Kraken gives only ~7 days of 15m bars without a backfill). The fan drew all 10 real equity curves (screen 21). |
| KB cards come from real data | ⚠️ partly | The detectors and `POST /kb/measure` work on any candles and are tested on hand-made candles; but the desk's Knowledge Base page still shows its Stage 1 demo cards. Not wired to `/kb` yet. |
| God's Eye shows live layers with attributions | ⚠️ partly | Backend: adsb.lol, USGS, Open-Meteo and Launch Library were fetched live in Stage 3, each with its attribution line. Desk: the globe now accepts the engine's layer events, but no engine-mode God's Eye screenshot was taken in this stage (Cesium in software WebGL is slow here). CelesTrak, FIRMS, AISStream and EIA were blocked or need keys. |
| Market impact alerts fire on test events | ✅ | `stage3_godseye.py` (13 tests): every rule on synthetic events, de-duplication, risk action only on "apply", never trades; plus 2 new tests that the risk gate obeys the flags. |
| Crop Watch shows a real Sentinel-2 NDVI tile | ❌ not as written | Crop Watch measures real Sentinel-2 L2A scenes from Planetary Computer (all 6 belts were measured live), but it uses the scene's `s2:vegetation_percentage` as an NDVI stand-in. There is no pixel NDVI tile on screen yet (needs rasterio and a tile renderer). |
| Licences logged | ✅ | `assets/LICENSES.md` → "Stage 3 data sources" and the Python libraries added. Open-Meteo free API is non-commercial; House PTR data is barred for commercial use (off by default). |

## Test results
- Stage 3 tests: 66 (`stage3_*.py`: backtest 17, data 11, God's Eye 13, KB 10, research 5, signals 10). All run offline.
- Whole engine: **159 passed** (`cd engine && .venv/bin/python -m pytest -q`; `pytest.ini` now collects `stage3_*.py` too).

## What falls back to synthetic data (always flagged)
Gold candles (no gold broker or CSV yet), shares, older crypto windows; God's Eye layers with no reachable host and no
cache; the offline research corpus when nothing online is new. Synthetic Lab results never create a strategy, and
synthetic layers never raise an alert.

## What is left
- Install Ollama on Ernest's machine and run a research round with it.
- Connect a gold broker (or drop a CSV into `<data dir>/candles/`), backfill BTC history, then re-run the Lab.
- Wire the Knowledge Base page to `/kb`; add a real NDVI tile for Crop Watch; take an engine-mode God's Eye screenshot on a machine with a GPU.
- Before sale: commercial terms for Open-Meteo, AISStream, Planetary Computer and the map tiles; legal advice on congressional trading data.
