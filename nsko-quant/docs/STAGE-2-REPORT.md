# NSKO QUANT · Stage 2 report: engine core, desktop shell and the 24/7 service

26 Nov 2026 · branch `nsko-quant` · built from `docs/ENGINE-CORE-NOTES.md`, `docs/DESKTOP-NOTES.md` and the Stage 4
integration · not committed.

## In plain English

NSKO QUANT is now a real desktop app wrapped around a real engine. The engine is a separate background program on
your computer: closing the window does not stop it. You create your account on first run (it lives only on your
computer, encrypted), check your licence offline, and unlock the desk with your password (and an authenticator code
if you turn 2FA on). The tray icon shows green / amber / red, and its menu can pause trading, hit the kill switch or
quit, even with the window closed.

This was checked end to end against the real engine (not a mock, as in the first Stage 2 screenshots): account,
recovery code, wrong and right password, licence valid / invalid / expired, settings, brokers, paper trades with
bracket orders, the audit trail. Windows and macOS installers are built by CI only, and CI has not run yet.

## What was built

**Engine core** (`ENGINE-CORE-NOTES.md`): FastAPI on 127.0.0.1:8787 with a WebSocket event bus; SQLite (WAL);
append-only hash-chained audit log; settings with the 9.4 defaults; Argon2id accounts with an encrypted data key,
recovery code, optional PIN and TOTP 2FA; offline Ed25519 licences (`tools/make-licence`); secrets vault (OS keychain,
or an AES-GCM file); paper broker with native brackets; ntfy and Telegram alerts (Telegram `/kill` from the paired
chat only); health + heartbeat + keep-awake; watchdog; reboot recovery (re-places a missing stop); internet-drop
handling; desk backup / restore; service files for systemd, launchd, Windows (NSSM) and Docker.

**Desktop shell** (`DESKTOP-NOTES.md`): Tauri 2, app id `uk.co.nsko.quant`, version 0.2.0. Close hides to the tray;
tray colour from `/health` every 4 s; tray menu with pause, kill switch and quit (native confirmations); sidecar engine
when no OS service answers; keychain commands (write-only from the webview); updater (placeholder feed),
notifications, autostart (`--hidden`), single instance. Linux AppImage and .deb were built and opened under Xvfb.

**UI wiring**: Demo / Live engine switch with fallback to demo data and back-off retries; lock screen; onboarding;
kill switch; Manual approve; settings; brokers; withdraw; paper & live; strategy book; God's Eye on CesiumJS.

**Stage 4 integration changes that complete Stage 2**: every endpoint and shape the desk assumed was reconciled with
the engine (`engine/CONTRACT.md`); CORS for the Tauri origins; WebSocket needs the session token; the tray authenticates
pause / quit with a local shared secret (`<data_dir>/shell.token`, owner-only) and the kill switch needs no login at all;
the PyInstaller one-file spec CI expects now exists and was built here (58 MB, `--version` OK, served `/health`);
the CI workflow is copied to the repo root; Settings gained ntfy / Telegram set-up with pairing and a test alert.

## Acceptance checks (master build plan, Stage 2)

| Check | Result | Evidence / honest note |
|---|---|---|
| Installs and opens on Windows / macOS | ❌ not verified | CI builds them (`/.github/workflows/nsko-quant-build.yml`), but **CI has not been run** and there is no Windows or Mac here. Only the Linux AppImage / .deb were built and opened (Xvfb). |
| Account create / login / wrong password | ✅ | e2e against the real engine (screens 02–05): create with a valid licence, recovery code shown once, reload asks for login, wrong password refused, right password unlocks. pytest: duplicate account, weak password, PIN lockout after 5 tries. |
| 2FA | ✅ engine · ⚠️ desk | TOTP set-up, required-at-login and wrong-code refusal are tested in pytest. The desk's 2FA step was shown in Stage 2 against a mock; it was not re-run against the real engine in the e2e. |
| Licence valid / invalid / expired | ✅ | e2e: expired (screen 01), damaged, and valid Pro licences, all checked offline by the engine; a bad licence also blocks account creation. pytest: forged payload, wrong key, garbage. |
| Closing the window keeps the engine trading (tray green) | ⚠️ by design, not re-tested | The engine is its own process (OS service or sidecar), so the window cannot stop it; the close-to-tray behaviour ran in the Linux build under Xvfb in Stage 2. The tray's new shared-secret code was **not compiled here** (disk too small for `cargo check`); CI compiles it. The tray's HTTP calls themselves were exercised by the e2e (pause with the secret, kill with no login). |
| Survives a reboot and a forced crash | ⚠️ partly | Reboot recovery is tested (positions reconciled, a missing stop re-placed); the paper broker persists its state; the watchdog restarts a stuck engine. A real reboot and a real `kill -9` under systemd / launchd / NSSM were not done here (no service manager in the container). |
| Keep-awake | ❌ not verified | Code paths for Windows (`SetThreadExecutionState`), macOS (`caffeinate`) and Linux (`systemd-inhibit`) exist; in this container `/health` honestly reports `failed: systemd-inhibit unavailable`. |
| Paper bracket trades | ✅ | e2e: two paper trades with native brackets (stop + target at the broker), scale-out at 1R, stop to breakeven, exit at target. pytest covers the fallback path and "close if no stop". |
| An audit entry per step | ✅ | e2e: `trade.open`, `position.scale_out`, `trade.exit` in the audit log and the hash chain verifies; every risk check is written to `risk_events`. |
| Phone alert | ❌ not sent to a phone | ntfy and Telegram sends are built and tested offline (and the new "Send a test alert" endpoint is tested with mocked channels); no ntfy topic or bot token exists here, so nothing reached a real phone. |

## Test results
- Engine: **159 passed** (`cd engine && .venv/bin/python -m pytest -q`).
- Desk: `npx tsc -b && npx vite build` passes.
- e2e: **53/53** (`node tools/e2e-stage4.cjs`; screenshots in `docs/screenshots/stage-4/`).

## What is faked or not real yet
- Update feed URL and updater key are placeholders; builds are unsigned.
- The Linux bundles built locally contain a placeholder sidecar; the real engine goes in through CI (the spec now exists).
- Esri / OSM map tiles need a commercial provider before sale.

## What is left
- Push to `nsko-quant` so CI runs; install the Windows and macOS builds on Ernest's machines; check the tray there.
- Test a real reboot and a forced crash with the OS service installed, and keep-awake on each OS.
- Pair a phone (ntfy topic or Telegram bot) and send the test alert.
- Code signing (steps in `DECISIONS.md`) and a real update feed.
- The tray's "Quit engine" stops the process; under an OS service with `Restart=always` it comes back. Needs a per-OS "stop the service" helper.
