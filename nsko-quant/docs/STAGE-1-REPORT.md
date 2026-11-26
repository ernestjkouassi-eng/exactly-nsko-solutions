# NSKO QUANT · Stage 1 report (brand + interface on demo data)

26 Nov 2026 · branch `nsko-quant` · code in `nsko-quant/app` · screenshots in `docs/screenshots/stage-1/`

## What was built
- **Brand:** `NSKO // QUANT` wordmark (NSKO in orange), lockups (dark and light) and a 1024 px app icon in `assets/brand/`, built from Ernest's own NSKO "N" mark. Design tokens live in `src/tokens.ts`, and all colours come from there.
- **Demo data simulator** (`src/demo/sim.ts`): seeded, emits the section 10 event names, drives every live number, ticker, chart and animation. A `DEMO DATA` chip shows in the top bar on every screen.
- **Shell:**
  - Two-row top bar: wordmark, JARVIS/SCOUT pulses, think budget, round counter, decisions count, PAPER mode with LIVE locked, hold-to-confirm kill switch (1.5 s), GMT clock.
  - Endless activity ticker, with verbs in their own colours.
  - Grouped sidebar with the orange active bar, live dots and amber badges.
  - JARVIS chat slide-out (Ctrl/⌘+J) with scripted demo answers.
  - Page change: 150 ms fade out, then 250 ms fade in with an 8 px rise.
- **Screens:**
  - **Overview:**
    - 8 KPI tiles.
    - BRAIN CORE: a 3,000-point rotating sphere on a lat/long wireframe. Source cards feed in along curved lines with travelling light. Every tested variant sprays a particle burst into "Variants tested".
    - Pipeline graph with a comet pulse.
    - Logbook.
    - Decisions cards (Approve slides the card out).
    - Mini equity curves and a latest-variants table.
  - **Lab:**
    - Tested/sieve bars.
    - WHY DO THEY FAIL? bars: the one that just changed glows gold.
    - Equity fan of 560 lines converging at the IS/OOS split, with the dashed bar at Sharpe 1.40, a self-drawing running test with a glowing head, and a scan beam. Hovering a line highlights it with a tooltip. Three colour modes.
    - Stat tiles and a variants table.
  - **Research:**
    - Nebula star field: 7 idea-type clusters with orbiting green source dots. New sources fly in.
    - NOW READING transcript, with trading terms lit as green chips.
    - SCOUT thought stream.
  - **Strategy Book:**
    - Filter tabs and search.
    - List with sparklines and 5-block quality bars.
    - Detail page: key figures, equity curve drawing in over 800 ms with the red drawdown mirrored underneath, monthly robustness grid, results by session.
  - **Knowledge Base:**
    - YOUR CHECK carousel: candle illustration, plain-English rule, code, Correct / Not correct.
    - Library groups.
    - Concept detail: bullish/bearish rules, a lifecycle ring animating 5/6 → 6/6, a candle-by-candle replay player, and three sources side by side.
  - **Agent Room (3D):**
    - Isometric office with 11 agents. JARVIS stands in orange on a ring platform with a halo.
    - Desk lights show working, a coffee cup idle, a red lamp stuck, a paper stack queued.
    - Packets fly desk to desk on every handoff event.
    - Camera modes Overview / Top down / Floor / Follow the work. Clicking an agent dollies the camera in and opens the NOW / BEFORE / HEARD / NEXT STEP panel.
    - Show-as-table toggle.
  - **God's Eye (shell):**
    - 3D globe with demo layers (flights, military, ships, satellites with orbit rings, quakes, fires, weather, launches, crops) and layer toggles.
    - Normal / Night-vision / Thermal sensor switch.
    - MARKET IMPACT cards: each says it "never opens a trade by itself".
    - 24 h timeline.
    - ALT-DATA LAB tab with Crop Watch, Oil Storage (glowing tank rings) and Car Counts (locked premium, generic "RETAILER", no logos).
  - **Live Desk:**
    - Lightweight Charts candles with entry, stop and target lines.
    - Order-flow overlay: green/red aggressive-volume bubbles, amber key-level zone, red resistance zone, tick-volume profile on the right edge (POC in orange).
    - Kronos fan of possible paths from the latest candle.
    - Market switcher (XAU, BTC, ETH, NVDA, AAPL).
    - Account panel with P&L ticking, open positions and orders.
    - Trade history with CSV button, and the risk warning in the footer.
  - **Trade Card:**
    - Nine-step tracker that runs itself.
    - Scanner counter to 5,900.
    - News and God's Eye checks.
    - Forecast fan.
    - Entry: Waiting → Triggered, with take-profit and stop zones.
    - Time Machine counting to 10,000, with paths between target and stop and the 29.4 / 25.5 / 45.1 % odds bar.
    - Size card and risk-gate ticks.
    - Order ticket: in Auto the lock opens and it stamps SENT ✓; in Manual it waits for Approve.
    - Exit with scale-out.
    - Analyst → bull/bear → risk → trader debate.
  - **Decisions:** full approval inbox.
  - **Paper & Live:** side-by-side results and the go-live checklist, including the typed phrase "I understand I can lose money".
  - **Brokers:** eight broker cards, Capital.com in demo with "Trading ✓ · Withdrawals OFF ✓", and the CMC "not supported" note.
  - **Engine:** status, uptime, keep-awake, CPU, RAM, heartbeat, redacted logs.
  - **Costs.**
  - **Settings:** risk limits with defaults, Auto/Manual, strategy updates, alerts, export/restore desk.
  - **Help:** FAQ and the risk warning.
  - **Onboarding wizard (7 steps):**
    1. Logo sting
    2. Account and licence
    3. 24/7 setup check
    4. Broker
    5. Risk limits
    6. Markets and mode
    7. Start on PAPER

## Acceptance checks
- [x] Every page in 6.2–6.13 exists, in English with NSKO branding (18 screenshots).
- [x] The demo simulator drives the live numbers; DEMO DATA is visible.
- [~] **60 fps:** measured in headless Chromium with **software** WebGL (no GPU). Results by page:
  - Overview: 47 fps.
  - Lab, Research, Strategies, Knowledge, Live Desk, Trade Card and every other 2D page: 60–61 fps.
  - Agent Room (3D): 32 fps.
  - God's Eye (3D): 13 fps.

  The 3D pages need a real GPU to measure honestly. Re-check on a mid-range laptop in Stage 2 (the Tauri build).
- [x] `prefers-reduced-motion`: CSS animations and transitions switch off, and canvas loops draw a single frame.
- [x] Screenshots saved in `docs/screenshots/stage-1/`.
- [x] This report.

## What is faked (on purpose, Stage 1)
- Everything on screen is demo data. Clearly labelled demo items include prices, variants, sources, agents, trades and alerts.
- JARVIS gives scripted answers.
- The God's Eye globe is procedural, not satellite imagery. CesiumJS and the live free feeds replace it in Stage 3.
- The onboarding stores nothing yet: no real account, licence check or keychain.
- The kill switch only locks the demo.

## What's left / notes
- **Reference material:**
  - The videos supplied cover God's Eye (two) and alt-data (one). Those two screens follow them: HUD readouts, yellow flights, cyan shipping lanes, satellite rings, thermal/night modes, tank rings, frost overlay, cars counted.
  - The main interface, trade-card, order-flow and forecast screens follow the text reference board, because there were no videos or PDF pages for those.
  - Add the master prompt and the reference board `.md` files to `docs/` as the source of truth.
- **Stage 2 (next):**
  - Tauri 2 shell and installers.
  - Python engine as a background service with tray icon, keep-awake and watchdog.
  - Accounts, licences, keychain.
  - Paper-trading simulator.
  - Database tables and audit log.
  - Swap the demo source for the engine WebSocket.
  - Updater and phone alerts.
- The production JS bundle is about 1.6 MB, mostly three.js. Code-splitting the 3D pages is a Stage 2 task.
