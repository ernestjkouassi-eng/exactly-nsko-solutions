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
