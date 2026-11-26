# NSKO QUANT · Stage 2 desktop shell and UI wiring

What was built on 26 Nov 2026, what works, and what is still open.

## 1. Desktop shell (`app/src-tauri`, Tauri 2)

| | |
|---|---|
| App id / name / version | `uk.co.nsko.quant` · NSKO QUANT · 0.2.0 |
| Window | 1600×960, minimum 1280×800, background #08080F, dark theme, centred |
| Close button | hides the window to the tray. The engine keeps running. |
| Tray / menu-bar icon | NSKO icon with a status dot: **green** trading, **amber** paused, **red** problem (engine not answering, kill switch on, status `problem/error`). Polls `GET /health` every 4 s from Rust, so it is right even with the window closed. |
| Tray menu | status line · Open NSKO QUANT · Pause / Resume new trades · Kill switch… (native confirmation) · Quit engine… (native confirmation) |
| Engine | if nothing answers on 127.0.0.1:8787 the shell starts the bundled sidecar `nsko-quant-engine` (`externalBin`, PyInstaller build) with `--host 127.0.0.1 --port 8787`; its output goes to the shell log. If the OS service already answers, the sidecar is not started. |
| Keychain | `keyring` crate (macOS Keychain, Windows Credential Manager, Linux Secret Service). Commands `keychain_set`, `keychain_has`, `keychain_delete`; there is deliberately no command that reads a secret back into the webview. Service `uk.co.nsko.quant`, account `broker:<id>:<demo|live>:key` / `:secret`. |
| Plugins | updater (placeholder feed `https://updates.example.com/nsko-quant/latest.json`, placeholder pubkey), notification (desktop alerts for `alert`, `kill_switch`, `order_filled`), autostart (`--hidden` = start to tray), single-instance (a second launch focuses the window), dialog, opener (broker withdrawal page in the browser), process (relaunch after update), shell (sidecar). |
| Icons | `assets/brand/nsko-quant-app-icon-1024.svg` → `rsvg-convert` 1024 PNG → `npx tauri icon` (PNG/ICO/ICNS) + three 64 px tray icons with the status dot. |
| CSP | self + `127.0.0.1:8787` (http/ws) + `tile.openstreetmap.org` + `server.arcgisonline.com` / `services.arcgisonline.com`. |

Shell files: `src-tauri/src/main.rs`, `tauri.conf.json`, `capabilities/default.json`, `Cargo.toml`, `icons/`, `binaries/README.md`.

## 2. Linux bundle: built

`npx tauri build --bundles appimage,deb` succeeded in this container (Ubuntu 24.04, Rust 1.97, after `apt-get install libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev patchelf build-essential libssl-dev libdbus-1-dev libxdo-dev`):

- `app/src-tauri/target/release/bundle/appimage/NSKO QUANT_0.2.0_amd64.AppImage` · **85.0 MiB** (the AppImage carries WebKitGTK and GStreamer)
- `app/src-tauri/target/release/bundle/deb/NSKO QUANT_0.2.0_amd64.deb` · **9.8 MiB**

Smoke test: the built binary was started under Xvfb. The 1600×960 window opened, the shell found no engine on :8787, started the sidecar, and the UI fell back to DEMO DATA with a notice (screenshot `docs/screenshots/stage-2/16-desktop-app-linux-xvfb.png`).

**Important:** these local bundles contain a *placeholder* sidecar (a 4-line shell script that exits), because the engine's PyInstaller spec does not exist yet. The real engine goes in through CI. `npm run engine:stub` writes the placeholder on a fresh clone so `tauri build` works without the engine.

The container's disk is capped (about 3 GB free); `npm cache clean` and removing pip/uv caches was needed to fit the Rust build.

## 3. CI (`nsko-quant/.github/workflows/build.yml`)

- **Must be copied to the repo root** as `.github/workflows/nsko-quant-build.yml`: GitHub only runs workflows from the root `.github`. Paths inside already assume the repo root.
- Triggers: push to `nsko-quant`, tags `quant-v*` (drafts a pre-release), manual run.
- Job `engine` (4 free runners: ubuntu-22.04, windows-latest, macos-15 arm64, macos-15-intel): Python 3.11, `pip install -r engine/requirements.txt` (or `pip install .` from a pyproject), `pyinstaller engine/nsko-quant-engine.spec` → `dist/nsko-quant-engine[.exe]` (onefile assumed), smoke test `--version`, upload.
- Job `desktop` (ubuntu-22.04 → .AppImage + .deb; windows-latest → .msi + NSIS .exe; macos-15 → universal .dmg): places the sidecar as `app/src-tauri/binaries/nsko-quant-engine-<target-triple>`, then `tauri-apps/tauri-action@v0`.
- macOS universal: PyInstaller cannot build one universal2 binary with numpy/pandas, so CI ships both engines as `Contents/Resources/engine/{arm64,x86_64}/` and the sidecar `nsko-quant-engine-universal-apple-darwin` is a 5-line launcher that picks the right one (`uname -m`). CI writes `tauri.macos.conf.json` for that resource mapping.
- Unsigned. Signing steps are in `docs/DECISIONS.md`. The workflow has not been run yet (no push was made).

## 4. UI wiring (`app/src`)

- **`source.ts`**: Demo data / Live engine switch. Engine mode probes `GET /health`, shows the lock screen, then opens `ws://127.0.0.1:8787/ws` with reconnect and backoff (1 s → 30 s, jittered). If the engine does not answer, or the socket drops 3 times, the desk falls back to the simulator with a notice and keeps retrying; when the engine is back it asks for login again. Desktop app defaults to engine, the browser to demo; the choice is remembered. `?source=demo|engine` overrides it, and `?engine=http://127.0.0.1:PORT` points at another local engine (development and tests only).
- **`store.ts`**: one `handle(ev)` used by both sources. New event handling: `kill_switch`, `decision_needed` (with `plan_id`), `alert`, `order_filled`, `gods_eye_event`, `market_impact`, and `engine_health.paused/killed`. Switching to the engine clears demo numbers.
- **`api.ts`**: every endpoint in the brief, plus the assumed extras below. Demo mode → demo data; engine offline → demo data and a notice; engine error → shown as an error.
- **Chips**: DEMO DATA only when the numbers are simulated; in engine mode an ENGINE chip (CHECKING / CONNECTING / ONLINE / RECONNECTING / OFFLINE / LOCKED). Both show during a fallback.
- **Onboarding** step 2: name, email, password (twice, 10+ characters), licence key with Check (`GET /licence/check`), optional 6-digit PIN and authenticator 2FA → `POST /account/create` → the recovery code shown once (a "written down" box must be ticked) → 2FA secret, confirmed with a code (`/account/totp/begin|confirm`). The token from create logs the desk in.
- **Lock screen**: email + password → if the engine answers `totp_required` / `pin_required` (or `{need}`) a second step asks for the 6-digit code. "Use demo data instead" is always there. The token is kept in memory only.
- **Kill switch** (hold 1.5 s): locks the desk at once, then `POST /kill`; a refusal is shown as a red, sticky alert telling the user to close at the broker. Re-enable asks first, then `POST /kill {action:"release"}`. The tray's kill switch updates the desk.
- **Trade Card** Manual → Approve calls `POST /trade/approve {plan_id}` (from the latest `decision_needed`).
- **Settings**: Data source card (Demo / Live engine, with connection state and a fallback banner), risk limits, trading mode, strategy updates and alerts loaded from `GET /settings` and saved with `POST /settings`; Desktop panel (start on boot, check for updates); Desk export/restore with a passphrase.
- **Brokers**: `GET /brokers`; Connect asks for key/secret/account and demo/live, stores them in the keychain, then `POST /brokers/{id}/connect` with the keychain reference (in a plain browser the key goes to the localhost engine instead, and is never stored by the UI).
- **Money → Withdraw** (section 9.7): balance strip from `GET /withdraw/helper`; 1 pause new trades → 2 optionally close positions (tick box) → 3 free amount + open the broker's withdrawal page → 4 "I have withdrawn · rescale and resume".
- **Paper & Live**: checklist from `GET /paperlive/checklist`; Go live posts the typed phrase.
- **Strategy Book**: `GET /strategies`, To paper / To live (`POST /strategies/{id}/promote`), Version history table with Roll back to vN (`POST /strategies/{id}/rollback`).
- **God's Eye**: CesiumJS 1.147, no ion (`Ion.defaultAccessToken = undefined`, geocoder off, no ion assets, no Google 3D Tiles, ellipsoid terrain). Basemaps Esri World Imagery / OpenStreetMap / Natural Earth II (bundled, offline). Layers from `gods_eye_event` (`{layer, id, lat, lon, alt_m?, label?, ts?}`) in point collections updated in place; MARKET IMPACT cards and globe markers from `market_impact` (`{id, title, asset, note, tone, lat?, lon?}`). Sensor modes are post-process stages (Cesium night vision; custom thermal palette). The 24 h timeline filters event layers by time; flights, ships and satellites show their latest position. An attribution line lists the basemap and the source of every enabled layer, with "DEMO POSITIONS" in demo mode. ALT-DATA LAB tab kept.
- **Code-splitting**: Agent Room, God's Eye and Live Desk are `React.lazy` chunks (Live Desk was moved to `pages/LiveDesk.tsx`). Main bundle about 500 kB; Cesium about 4.2 MB, loaded only on God's Eye.

`npx tsc -b && npx vite build` passes.

## 5. Screenshots (`docs/screenshots/stage-2/`, 1920×1080)

01 onboarding account step · 02 recovery code shown once · 03 lock (password) · 04 lock (authenticator) · 05 overview on the engine (mock) · 06 settings, source = Live engine, settings from the engine · 07 withdraw from the engine · 08 settings, source = Demo · 09 engine offline → demo fallback notice · 10 withdraw (demo) · 11 God's Eye, Cesium + Esri imagery · 12 night vision · 13 thermal · 14 OpenStreetMap basemap · 15 Strategy Book version history · 16 the real Linux desktop build running under Xvfb.

Screens 03–07 ran against a throwaway mock of the engine contract (kept outside the repo), because the real engine HTTP server was not ready. `tools/shots-stage2.cjs` re-creates them.

## 6. Gaps and notes for the engine agents

> **Resolved in the Stage 4 integration (26 Nov 2026).** Every item below was reconciled; see `engine/CONTRACT.md` (HTTP contract table) and `docs/STAGE-4-REPORT.md`. Kept here as the record of what was assumed.

1. **Assumed endpoints / shapes to confirm or add** (also in DECISIONS.md): `POST /withdraw/helper {action}`; `POST /kill {action:"release"}`; `POST /engine/shutdown`; `/health` fields `status, paused, killed, account_exists, uptime, cpu, ram, heartbeat`; login error codes `totp_required` / `pin_required` (FastAPI `detail:{code,msg}` is understood); `POST /account/create` accepts `pin` (2FA set-up uses the engine's existing `totp_begin/confirm` via `/account/totp/begin|confirm`); `GET /licence/check?key=`; `POST /settings {trading_paused}` for pause and `{mode:"live", confirm_phrase}` for go-live; desk export returns `{filename, data_b64}`; `POST /brokers/{id}/connect` takes `{environment, keychain_service, keychain_account, account_id}`; WebSocket accepts `?token=`.
2. **CORS**: the engine must allow the origins `tauri://localhost`, `http://tauri.localhost` (Windows) and `http://localhost:5173/4173` (dev).
3. **Tray actions have no session token** (they come from the Rust shell with `X-NSQ-Client: desktop-shell`). The engine should accept `/kill` (safety first) and pause from localhost without a session, or the shell needs a local shared secret file.
4. The sidecar is started with `--host 127.0.0.1 --port 8787`, and `--version` is used as the CI smoke test; the PyInstaller entry point should accept these.
5. Not built here: Windows and macOS bundles (need those OSes; CI covers them), code signing, a real update feed, and a run of the CI workflow.
6. Esri World Imagery and the OSM tile servers need a commercial tile provider or key before sale (DECISIONS.md).
7. God's Eye ran at only a few fps in headless *software* WebGL (SwiftShader, 1920×1080). On a real GPU Cesium normally holds 60 fps with this many points; check it on Ernest's machines. All 2D canvases are unchanged from Stage 1.
8. Live Desk, Lab, Research and Agent Room still draw their own demo overlays (Kronos fan, key levels, the agent layout) even in engine mode; they need engine events for those parts in Stage 3.
9. The JARVIS panel still answers from the demo script in both modes.
