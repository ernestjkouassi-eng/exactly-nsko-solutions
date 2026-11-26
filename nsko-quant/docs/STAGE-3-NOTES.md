# NSKO QUANT · Stage 3 notes (data, research, Knowledge Base, Lab, God's Eye backend)

Date: 26 Nov 2026. Code: `engine/nsq/data`, `engine/nsq/research`, `engine/nsq/lab`, `engine/nsq/godseye`. Tests: `engine/tests/stage3_*.py`.

## In plain English
The engine can now:
- fetch real bitcoin and ether prices and live trades from Kraken;
- draw the volume profile and flag big orders;
- read research from GitHub and arXiv, summarise it, and turn ideas into strategy recipes;
- test each recipe ten ways against a strict pass mark, with costs and overfitting checks;
- keep a Knowledge Base of trading concepts, measured on your own data;
- watch flights, earthquakes, weather, launches and satellites for events that can move markets.

It never places a trade from God's Eye. When a source cannot be reached, it uses the last saved copy. If there is no saved copy, it uses made-up practice data, which is always labelled `synthetic=True`.

## What was built

### nsq/data
- **`candles.get(market, timeframe, start, end)`** follows the contract. It returns closed bars only, with a UTC index. It tries sources in this order:
  1. registered broker providers (`register_provider`; the paper broker already calls `get`);
  2. the CSV cache in `<data_dir>/candles/`;
  3. Kraken public OHLC (crypto);
  4. seeded synthetic data.

  `df.attrs` holds `source`, `synthetic`, `volume_kind` (exchange / tick / synthetic-…) and `partial`. Kraken OHLC gives only the latest 720 bars, so `backfill_kraken_trades()` builds deeper 1-minute history from Kraken's public Trades endpoint, at about one request a second. `resample()` keeps only buckets that have closed.
- **Synthetic fallback** (`synthetic.py`): GARCH(1,1) volatility clustering with Student-t (fat-tailed) shocks, scaled to each market's yearly volatility (gold about 15 %, BTC about 60 %). It adds a London/New York activity curve, slow trend regimes, volume linked to how far price moves, and gold's weekend close. It is seeded per market and timeframe, and built one calendar year at a time, so asking for a longer window never changes bars you already had.
- **Order flow** (`orderflow.py`) uses the Kraken WebSocket v2 `trade` channel, which gives true trade-by-trade volume with the taker side. Trades with the same timestamp and side are merged into one aggressive order, and an `orderflow_bubble` fires when that order is in the top percentile. `profile_update` sends POC, VAH, VAL, LVN, HVN, bins and cumulative delta every few seconds. This was tested live: bubbles and profile updates arrived.
- **Gold uses a tick-volume profile** (`TickProfile`, and `profile.from_candles` on gold data). It is labelled "tick-volume profile (CFD: no exchange volume)". CFD brokers report no exchange volume, only how many times the price changed, so for gold the profile shows activity, not traded size.
- **News and events** (`news.py`, 8.2). Only headlines and links are kept.
  - **GDELT** DOC 2.0 API.
  - **RSS / Atom feeds.** robots.txt is checked first, and the XML parser refuses DTDs.
  - **Economic calendar.** `econ_calendar.json` is the fallback: FOMC 2026 dates and recurring rules for NFP, jobless claims and the EIA report. It is merged with `news.calendar_file` and `news.events`, and has `in_blackout()`. The engine core's `trading/news.py` already reads it.
  - **SEC EDGAR**: the current 8-K feed and company submissions.
  - **US House PTRs**: context only, weeks late, and off by default (see the licences section).
  - **Senate**: a link only.
  - **13F**: context only.
- `python -m nsq.data.probe` checks every host once.

### nsq/research (8.3): the JARVIS team
- The agents are JARVIS, SCOUT, READER, WATCHER, SUMMARISER 1–3, TERM-CHECKER and RECIPE-MAKER (`pipeline.run_round`).
- **SCOUT** searches:
  - GitHub search plus each repository's README, recording the repository's own licence;
  - arXiv, limited to the q-fin categories;
  - YouTube Data API (bring your own key; transcripts are optional and off by default);
  - RSS feeds.

  If nothing online is new, it falls back to a small built-in set of notes, flagged synthetic.
- **WATCHER** highlights trading terms. It rejects hype ("always wins", "guaranteed") and items that are not about trading.
- **SUMMARISERS** use local **Ollama** (`/api/generate`, JSON format) when it is running at localhost:11434. Otherwise they use a deterministic offline summary that picks out sentences plus keyword scores for the idea type. Ollama's answers are checked: the idea type must be one of the seven.
- **TERM-CHECKER** queues terms the Knowledge Base does not have yet. They are added to the `terms` table and to the Knowledge Base at lifecycle step 1.
- **RECIPE-MAKER** writes recipe JSON in the contract format, built from the seed templates, for the market and timeframe it detects.
- **Daily compute budget** is set by `research.daily_budget` (default 50 "think units"). A round pauses with a PAUSE log line when the budget runs out. `budget_update` sends `{used, of, day, days (left in month), mode}`.
- **Events and storage.** Each step emits ticker_log, agent_status, agent_handoff, source_added, summary_done, term_found and recipe_created. Results are stored in the `sources`, `summaries`, `terms`, `recipes` and `research_budget` tables.
- This was tested live: a GitHub and arXiv round saved 5 sources and made 5 recipes. The offline round runs in the tests.

### nsq/lab (8.4)
- **`signals.generate(recipe, candles)`** follows the contract and uses closed bars only. It has four generators:
  - `ema_cross`: the trend follower;
  - `orb`: opening-range breakout;
  - `vwap_reversion`: mean reversion to the session VWAP;
  - `nsko_of_1`: the NSKO-OF-1 recipe.
- **NSKO-OF-1** ("react, don't predict"):
  - **Levels first:** the prior session's volume profile (VAH, VAL, POC, LVN), the prior session's high and low, and unfilled higher-timeframe fair value gaps. These only become usable once that higher-timeframe bar has closed.
  - **Market state:** balanced, or imbalanced (accepted outside the prior value area for 3 bars).
  - **Location:** it acts only at a mapped level.
  - **Confirmation:** a sweep and reclaim of the level, or aggressive volume (a volume spike with the close in the trade's direction).
  - **Stop and target:** the stop goes just beyond the swept extreme. The target is the next profile level, or the POC when the market is balanced, with an R-multiple fallback and a minimum R:R.
  - **Timeframe pairs:** 15m+3m (gold) or 1h+5m (BTC).
  - **Session filter:** London and New York for gold; 24/7 with a liquidity filter for crypto.
  - **News:** an optional news-blackout filter.
- **Backtester** (`backtest.py`):
  - **Fills:** entry at the next bar's open. If one bar touches both the stop and the target, the stop counts first. A gap through the stop fills at the open.
  - **Costs:** spread (fixed or in basis points), slippage on market fills, commission per side, and overnight funding per 22:00 UTC rollover.
  - **Equity:** R-based, compounding at `lab.risk_pct`.
  - **Speed:** exits are found with numpy per trade.
  - **Settings:** cost profiles by market type in `lab.costs.<kind>`.
- **Walk-forward** uses IS 2009–2019 and OOS 2020–now. If the history does not reach both sides of that line, it falls back to a 70/30 split by time.
- **The bar:** OOS Sharpe ≥ 1.40 after costs, at least 30 OOS trades, max drawdown 20 %, and stability under ±20 % parameter changes (worst case at least 0.5 × the base result and above 0). It also checks:
  - PBO ≤ 0.5 (CSCV across the 10 variants, 16 blocks);
  - how much Sharpe is lost from IS to OOS (at most 0.6);
  - that the strategy beats at least 90 % of random-entry runs.

  Every threshold lives in the `lab.bar.*` settings. The outcomes are clear, sieve or failed, with the `why` reason the UI uses.
- **Monte Carlo** reshuffles and bootstraps the trades to give drawdown odds and a p5/p50/p95 fan.
- **Variants:** 10 seeded parameter sets per recipe.
- **Events and storage:** `variant_tested` uses the exact contract payload, plus `backtest_done`. Results go to the `variants` and `backtests` tables, with a downsampled equity curve (300 points) for the fan, the Monte Carlo result, stability and chance. A strategy row is only created from **real** data that cleared the bar; synthetic results never become strategies.
- **Seed pack** (`lab/seed.py`): NSKO-OF-1 XAU, NSKO-OF-1 BTC, Trend-XAU, ORB-XAU and VWAP-Rev-BTC. They are written to `recipes` and to the core `strategies` / `strategy_versions` tables with status "lab".

### Knowledge Base (8.5), in `nsq/lab/kb.py` and `nsq/lab/detectors.py`
- There are 12 concepts. Each one has a plain-English rule, a bullish and a bearish condition, its code function (name and source), stats from the client's own data (count, % filled, average size and size as % of price), 3 sources, the user's verdict (keep / drop / unsure) and a 6-step lifecycle: found → explained → coded → measured → tested → verdict.
- The detectors are: fair value gap, order block, liquidity sweep, break of structure, change of character, displacement, swing high/low, equal highs/lows, inside bar, Asia range and opening range. Value area / POC uses `profile.from_candles`.
- Every detector reports the bar at which a pattern is **confirmed**, so none of them look ahead. A test checks this.

### nsq/godseye (8.6)
- **Layers.** Each has an attribution line and an on/off flag in `godseye.layer.<name>.enabled`:
  - flights: adsb.lol `/v2/mil`;
  - ships: AISStream, bring your own key, off by default;
  - satellites: CelesTrak GP, with a sub-satellite point if `sgp4` is installed;
  - quakes: USGS;
  - fires: NASA FIRMS, bring your own MAP_KEY, off by default;
  - weather: Open-Meteo, with the option `godseye.weather_model = gfs_seamless` for NOAA GFS;
  - launches: Launch Library 2.

  OpenSky, Cesium ion, Google 3D Tiles, CCTV and TeleGeography are not used.
- **MARKET IMPACT** (`impact.py`) runs the rules:
  - tanker slowdown at Hormuz, Bab-el-Mandeb or Suez → oil plus a gold watch;
  - a surge in military flights in 5 regions → safe-haven watch;
  - an M6+ quake within 150 km of 10 mines or ports → metals;
  - frost, heat or a dry week in a crop belt → coffee, cocoa, wheat or corn;
  - a drop in vegetation (NDVI), fires, and EIA stock surprises.

  Each alert sends a `market_impact` event: event → assets → JARVIS note → an optional risk action (cut_size / pause_new) → `opens_trade: false`. Risk actions are only suggestions unless `godseye.risk_actions = "apply"`. Applied actions go to `godseye_risk_flags`, and `impact.active_risk_flags(asset)` is there for the risk gate. Alerts are deduplicated per day, and synthetic layers never raise one.
- **ALT-DATA LAB** (`altdata.py`):
  - **Crop Watch** uses Sentinel-2 L2A scene search on Microsoft Planetary Computer (no key). It compares the cloud-adjusted `s2:vegetation_percentage` for the last 30 days with the same window a year ago, as an NDVI stand-in, over Minas Gerais coffee, Côte d'Ivoire and Ghana cocoa, Kansas and Ukraine wheat, and Iowa corn. It adds Open-Meteo frost and heat warnings. This was tested live: all 6 belts were measured.
  - **Oil Storage V1** uses EIA v2 series WCESTUS1 (bring your own key), cached.
  - **Car Counts** is a locked premium placeholder.
  - All of these emit `gods_eye_event`.

### FastAPI routers (for the engine core to mount)
`nsq/data/api.py`, `nsq/research/api.py`, `nsq/lab/api.py` and `nsq/godseye/api.py` each expose `router` (an APIRouter). Their paths are `/data/*`, `/research/*`, `/lab/*` with `/kb/*`, and `/godseye/*`. `nsq/app.py` already mounts all four.

**For the core agent:** these routers have no session dependency of their own. If the Lab, research and God's Eye endpoints should need a sign-in, mount them with `app.include_router(r, dependencies=[Depends(need_session)])`. POSTs are already covered by the app's X-NSQ-Client CSRF guard.

## Hosts: reachable vs blocked
Each host was probed from the build sandbox on 26 Nov 2026. A second probe ran after the coordinator opened more hosts.

| Host | Result |
|---|---|
| api.kraken.com, ws.kraken.com | **reachable**: live OHLC and the trade stream were tested |
| api.github.com | **reachable** for search. README reads were refused by the sandbox's GitHub proxy (a sandbox rule, not GitHub's), so READER fell back to the description |
| export.arxiv.org (https) | **reachable** |
| api.adsb.lol | **reachable**: /v2/mil returned live military aircraft |
| earthquake.usgs.gov | **reachable** |
| api.open-meteo.com | **reachable** |
| planetarycomputer.microsoft.com | **reachable**: STAC search tested |
| ll.thespacedevs.com | **intermittent**: worked once, then timed out (15 requests/hour free tier) |
| api.gdeltproject.org | **throttled**: answered HTTP 429 ("one request every 5 seconds"), then reset connections |
| www.sec.gov | **reachable**: 403 until a User-Agent naming you is set (SEC rule), so it is off until `sec.user_agent` is set |
| www.googleapis.com | reachable (403 without a key) |
| celestrak.org | **blocked** (timeouts and resets): falls back to cache or synthetic |
| firms.modaps.eosdis.nasa.gov (API) | **blocked** (reset): bring your own key anyway |
| stream.aisstream.io, api.eia.gov, disclosures-clerk.house.gov, rss.arxiv.org, www.federalreserve.gov, www.youtube.com | **blocked** by the sandbox proxy |
| localhost:11434 (Ollama) | not running in the sandbox, so the offline summariser was used |
| docs.kraken.com, aisstream.io, api.adsb.lol/docs | blocked, so the docs could not be re-read. The Kraken formats were confirmed against live responses instead |

On the client's own computer, none of these sandbox blocks apply.

## Tests
`cd engine && .venv/bin/python -m pytest tests/stage3_*.py`: **66 passed** in about 11 s. All tests run offline: the network is switched off inside the tests.

| File | Tests | Covers |
|---|---|---|
| stage3_signals.py | 10 cases | **no look-ahead for every generator** (all 5 seed recipes plus an NSKO-OF-1 variant): signals are unchanged when future bars are added, checked at 3 cut points; the signal shape; the gold session filter |
| stage3_backtest.py | 17 | backtester maths on a known series (exactly 2R; costs worked out by hand; stop first when a bar touches both; gap through the stop; short trades and funding nights; one position at a time; drawdown and Sharpe); **walk-forward split** (calendar and fallback); **PBO toy cases** (noise ≈ 0.5, a real edge < 0.05, overfit by construction > 0.5); Sharpe decline; Monte Carlo; chance score; runner payloads match the contract; synthetic results never become strategies; variants ×10; the bar thresholds come from settings |
| stage3_godseye.py | 13 | **market-impact rules on synthetic events** (Hormuz tankers, military surge, M6 quake near a mine against far or small ones, coffee frost and cocoa heat, NDVI, EIA, deduplication, risk action only when "apply", never trades); layers fall back to synthetic then cache; bring-your-own-key layers; an attribution and flag for every layer |
| stage3_kb.py | 10 | **KB detectors on hand-made candles** (bullish and bearish FVG, swing confirmation delay, BOS then CHoCH, liquidity sweep, displacement, order block, inside bar, equal highs, Asia range); no detector looks ahead; lifecycle and stats |
| stage3_data.py | 11 | synthetic data is flagged, stable and realistic; offline fallback; cache and closed-bar resampling; broker provider; POC and value area; tick-volume label; Kraken parser and bubble merging; calendar (NFP first Friday, FOMC) and blackout; RSS/Atom headline-only parsing and DTD refusal; opt-in sources |
| stage3_research.py | 5 | a full offline round (every event type and ticker verb, all 4 tables, hype rejected, idea types valid, recipes valid); no duplicates; the budget pauses a round; classifier; deterministic summary |

`pytest tests` collects only `test_*.py`, because that is pytest's default. To run everything, use `pytest -o python_files="test_*.py stage3_*.py" tests`: **132 passed**, Stage 2 and Stage 3 together. The core agent could add `python_files` to the pytest config, which is not my file. The tests use `engine/.venv`, built by the core agent from `requirements.txt`. My own temporary `.venv3` was deleted.

## What falls back to synthetic data (flagged `synthetic=True`)
- **Candles** for any market with no broker, cache or Kraken data: gold (until a broker or a CSV is connected), shares, and any crypto window older than Kraken's 720-bar OHLC limit unless backfilled. A Lab run on synthetic data says so in its log line, `backtest_done` and every stored row, and never creates a strategy. All seed recipes currently fail the bar on synthetic data, as they should: random-walk data has no edge to find once costs are paid.
- **Research**: the built-in offline notes, used when no online source has anything new.
- **God's Eye layers** with no reachable host and no cache: a small seeded set of points. Synthetic layers never raise market-impact alerts.
- **Kraken trade stream down**: no bubbles or profile are invented. The stream logs PAUSE and retries with back-off.
- **No Ollama**: the deterministic offline summariser (not synthetic, just simpler).

## Licences
The full list is in `assets/LICENSES.md` under "Stage 3 data sources". In short:
- Kraken public data (personal use, no redistribution).
- GDELT (open, citation).
- SEC EDGAR, USGS, EIA and NOAA GFS: US public domain.
- House PTRs: **commercial use barred by US law**, so off by default.
- Senate eFD: link only.
- GitHub: each repository's own licence is recorded.
- arXiv: metadata CC0.
- YouTube API terms: bring your own key; transcripts off by default.
- adsb.lol: ODbL 1.0.
- AISStream: bring your own key, terms not confirmed.
- CelesTrak: credit, fetch at most every 2 hours.
- NASA FIRMS: bring your own key, open.
- Open-Meteo: CC BY 4.0, and the **free API is non-commercial**; a paid product needs a plan (`open_meteo_api_key` switches to the customer API).
- Launch Library 2: free tier, 15 per hour.
- Planetary Computer: terms to re-check; Sentinel-2 is Copernicus open data.

Python libraries: websockets (BSD-3), defusedxml (PSF), sgp4 (MIT), youtube-transcript-api (MIT), pandas and numpy (BSD-3).

## Open items for Ernest
- Before selling, check the Open-Meteo, AISStream and Planetary Computer terms for commercial use, and get legal advice on congressional trading data.
- Free keys you can add when you want those layers (stored in the keychain, never in settings): YouTube Data API, AISStream, NASA FIRMS MAP_KEY and EIA. For SEC, set `sec.user_agent` to your name and email.
- Connect a gold broker, or drop a CSV into `<data dir>/candles/XAUUSD_3m.csv`, so NSKO-OF-1 XAU runs on real tick volume. Then run the Lab.
