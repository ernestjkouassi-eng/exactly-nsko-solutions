// NSKO QUANT desktop shell (Tauri 2).
// - The window is only a view. Closing it hides it to the tray; the engine keeps trading.
// - The engine is the local Python service on 127.0.0.1:8787. If the OS service is not answering,
//   the shell starts the bundled sidecar (PyInstaller build of nsko-quant/engine).
// - Tray icon colour: green = trading, amber = paused, red = problem / engine not answering / kill switch on.
// - Broker keys go into the OS keychain. The webview can store and delete a key, never read one back.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use serde::Serialize;
use tauri::image::Image;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, RunEvent, WindowEvent, Wry};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const ENGINE: &str = "http://127.0.0.1:8787";
const KEYCHAIN_SERVICE: &str = "uk.co.nsko.quant";
const TRAY_GREEN: &[u8] = include_bytes!("../icons/tray/tray-green.png");
const TRAY_AMBER: &[u8] = include_bytes!("../icons/tray/tray-amber.png");
const TRAY_RED: &[u8] = include_bytes!("../icons/tray/tray-red.png");

#[derive(Clone, Copy, PartialEq, Eq, Serialize, Debug)]
#[serde(rename_all = "lowercase")]
enum Light {
    Green,
    Amber,
    Red,
}

#[derive(Clone, Serialize, Debug)]
struct EngineStatus {
    light: Light,
    text: String,
    reachable: bool,
    paused: bool,
    killed: bool,
    sidecar: bool,
}

struct Shell {
    status: Mutex<EngineStatus>,
    sidecar: Mutex<Option<CommandChild>>,
    status_item: MenuItem<Wry>,
    pause_item: MenuItem<Wry>,
}

// ---------- engine HTTP (blocking, short timeouts, never on the UI thread)
fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(Duration::from_millis(1200))
        .timeout(Duration::from_secs(4))
        .build()
}

fn health() -> Option<serde_json::Value> {
    agent()
        .get(&format!("{ENGINE}/health"))
        .set("X-NSQ-Client", "desktop-shell")
        .call()
        .ok()?
        .into_json()
        .ok()
}

fn post(path: &str, body: serde_json::Value) -> Result<(), String> {
    agent()
        .post(&format!("{ENGINE}{path}"))
        .set("X-NSQ-Client", "desktop-shell")
        .send_json(body)
        .map(|_| ())
        .map_err(|e| e.to_string())
}

fn read_status(sidecar: bool) -> EngineStatus {
    match health() {
        None => EngineStatus {
            light: Light::Red,
            text: "Engine not answering".into(),
            reachable: false,
            paused: false,
            killed: false,
            sidecar,
        },
        Some(h) => {
            let b = |k: &str| h.get(k).and_then(|v| v.as_bool()).unwrap_or(false);
            let s = h.get("status").and_then(|v| v.as_str()).unwrap_or("ok").to_lowercase();
            let killed = b("killed") || b("kill_switch");
            let paused = b("paused") || b("trading_paused") || s == "paused";
            let problem = killed || matches!(s.as_str(), "problem" | "error" | "degraded" | "down");
            let (light, text) = if problem {
                (Light::Red, if killed { "Kill switch on · trading locked".into() } else { format!("Problem · {s}") })
            } else if paused {
                (Light::Amber, "Paused · no new trades".into())
            } else {
                (Light::Green, "Trading".into())
            };
            EngineStatus { light, text, reachable: true, paused, killed, sidecar }
        }
    }
}

fn apply_status(app: &AppHandle, st: EngineStatus) {
    let shell = app.state::<Shell>();
    let changed = {
        let mut cur = shell.status.lock().unwrap();
        let changed = cur.light != st.light || cur.text != st.text || cur.paused != st.paused;
        *cur = st.clone();
        changed
    };
    if !changed {
        return;
    }
    if let Some(tray) = app.tray_by_id("main") {
        let bytes = match st.light {
            Light::Green => TRAY_GREEN,
            Light::Amber => TRAY_AMBER,
            Light::Red => TRAY_RED,
        };
        if let Ok(img) = Image::from_bytes(bytes) {
            let _ = tray.set_icon(Some(img));
        }
        let _ = tray.set_tooltip(Some(format!("NSKO QUANT · {}", st.text)));
    }
    let dot = match st.light {
        Light::Green => "●",
        Light::Amber => "◐",
        Light::Red => "○",
    };
    let _ = shell.status_item.set_text(format!("{dot} {}", st.text));
    let _ = shell.pause_item.set_text(if st.paused { "Resume new trades" } else { "Pause new trades" });
    let _ = shell.pause_item.set_enabled(st.reachable);
    let _ = app.emit("engine-status", st);
}

fn refresh(app: &AppHandle) {
    let sidecar = app.state::<Shell>().sidecar.lock().unwrap().is_some();
    apply_status(app, read_status(sidecar));
}

// ---------- sidecar: only when the OS service is not already answering on :8787
fn ensure_engine(app: &AppHandle) {
    if health().is_some() {
        println!("[shell] engine service already answering on :8787");
        return;
    }
    let cmd = match app.shell().sidecar("nsko-quant-engine") {
        Ok(c) => c,
        Err(e) => {
            eprintln!("[shell] no sidecar: {e}");
            return;
        }
    };
    match cmd.args(["--host", "127.0.0.1", "--port", "8787"]).spawn() {
        Ok((mut rx, child)) => {
            println!("[shell] started engine sidecar pid {}", child.pid());
            *app.state::<Shell>().sidecar.lock().unwrap() = Some(child);
            let h = app.clone();
            tauri::async_runtime::spawn(async move {
                while let Some(ev) = rx.recv().await {
                    match ev {
                        CommandEvent::Stdout(l) => println!("[engine] {}", String::from_utf8_lossy(&l).trim_end()),
                        CommandEvent::Stderr(l) => eprintln!("[engine] {}", String::from_utf8_lossy(&l).trim_end()),
                        CommandEvent::Terminated(p) => {
                            eprintln!("[shell] engine sidecar exited: {:?}", p.code);
                            *h.state::<Shell>().sidecar.lock().unwrap() = None;
                            refresh(&h);
                        }
                        _ => {}
                    }
                }
            });
        }
        Err(e) => eprintln!("[shell] could not start the engine sidecar: {e}"),
    }
}

fn show_main(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.unminimize();
        let _ = w.show();
        let _ = w.set_focus();
    }
}

fn confirm(app: &AppHandle, title: &str, msg: &str, ok: &str, then: impl FnOnce(AppHandle) + Send + 'static) {
    let h = app.clone();
    app.dialog()
        .message(msg)
        .title(title)
        .kind(MessageDialogKind::Warning)
        .buttons(MessageDialogButtons::OkCancelCustom(ok.into(), "Cancel".into()))
        .show(move |yes| {
            if yes {
                then(h)
            }
        });
}

fn on_menu(app: &AppHandle, id: &str) {
    match id {
        "open" => show_main(app),
        "pause" => {
            let paused = app.state::<Shell>().status.lock().unwrap().paused;
            let h = app.clone();
            thread::spawn(move || {
                if let Err(e) = post("/settings", serde_json::json!({ "trading_paused": !paused })) {
                    eprintln!("[shell] pause failed: {e}");
                }
                refresh(&h);
            });
        }
        "kill" => confirm(
            app,
            "Kill switch",
            "Cancel all orders, close all positions and lock trading?\n\nTrading stays locked until you re-enable it on the desk.",
            "Kill everything",
            |h| {
                thread::spawn(move || {
                    let r = post("/kill", serde_json::json!({ "confirm": true, "source": "tray" }));
                    let _ = h.emit("tray-kill", r.is_ok());
                    if let Err(e) = r {
                        let _ = h
                            .dialog()
                            .message(format!("The engine did not answer the kill switch: {e}\n\nClose positions at your broker directly."))
                            .title("Kill switch failed")
                            .kind(MessageDialogKind::Error)
                            .blocking_show();
                    }
                    refresh(&h);
                });
            },
        ),
        "quit" => confirm(
            app,
            "Quit engine",
            "Stop the NSKO QUANT engine and close the app?\n\nNothing will trade, manage stops or send alerts until you start it again. Orders already at the broker stay there.",
            "Quit engine",
            |h| {
                thread::spawn(move || {
                    let _ = post("/engine/shutdown", serde_json::json!({ "confirm": true }));
                    if let Some(child) = h.state::<Shell>().sidecar.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                    h.exit(0);
                });
            },
        ),
        _ => {}
    }
}

// ---------- commands for the webview
#[tauri::command]
fn engine_status(state: tauri::State<Shell>) -> EngineStatus {
    state.status.lock().unwrap().clone()
}

#[tauri::command]
fn keychain_set(account: String, secret: String) -> Result<(), String> {
    keyring::Entry::new(KEYCHAIN_SERVICE, &account)
        .and_then(|e| e.set_password(&secret))
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn keychain_has(account: String) -> bool {
    keyring::Entry::new(KEYCHAIN_SERVICE, &account)
        .and_then(|e| e.get_password())
        .is_ok()
}

#[tauri::command]
fn keychain_delete(account: String) -> Result<(), String> {
    match keyring::Entry::new(KEYCHAIN_SERVICE, &account).and_then(|e| e.delete_credential()) {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(e.to_string()),
    }
}

fn main() {
    let hidden = std::env::args().any(|a| a == "--hidden");

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| show_main(app)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--hidden"]),
        ))
        .setup(move |app| {
            let h = app.handle();
            let status_item = MenuItem::with_id(h, "status", "○ Checking the engine…", false, None::<&str>)?;
            let open = MenuItem::with_id(h, "open", "Open NSKO QUANT", true, None::<&str>)?;
            let pause_item = MenuItem::with_id(h, "pause", "Pause new trades", false, None::<&str>)?;
            let kill = MenuItem::with_id(h, "kill", "Kill switch…", true, None::<&str>)?;
            let quit = MenuItem::with_id(h, "quit", "Quit engine…", true, None::<&str>)?;
            let sep = PredefinedMenuItem::separator(h)?;
            let sep2 = PredefinedMenuItem::separator(h)?;
            let menu = Menu::with_items(h, &[&status_item, &sep, &open, &pause_item, &sep2, &kill, &quit])?;

            app.manage(Shell {
                status: Mutex::new(EngineStatus {
                    light: Light::Red,
                    text: "Checking the engine…".into(),
                    reachable: false,
                    paused: false,
                    killed: false,
                    sidecar: false,
                }),
                sidecar: Mutex::new(None),
                status_item,
                pause_item,
            });

            TrayIconBuilder::with_id("main")
                .icon(Image::from_bytes(TRAY_RED)?)
                .tooltip("NSKO QUANT")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, ev| on_menu(app, ev.id.as_ref()))
                .on_tray_icon_event(|tray, ev| {
                    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = ev {
                        show_main(tray.app_handle());
                    }
                })
                .build(app)?;

            if !hidden {
                show_main(h);
            }

            // Start the sidecar if needed, then poll /health every 4 s for the tray colour.
            let h2 = h.clone();
            thread::spawn(move || {
                ensure_engine(&h2);
                loop {
                    refresh(&h2);
                    thread::sleep(Duration::from_secs(4));
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the window hides it. The engine keeps running.
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![engine_status, keychain_set, keychain_has, keychain_delete])
        .build(tauri::generate_context!())
        .expect("error while building NSKO QUANT");

    app.run(|app, ev| {
        #[cfg(target_os = "macos")]
        if let RunEvent::Reopen { .. } = ev {
            show_main(app);
        }
        if let RunEvent::ExitRequested { api, code, .. } = &ev {
            // Last window hidden is not a reason to exit; only an explicit exit (Quit engine) has a code.
            if code.is_none() {
                api.prevent_exit();
            }
        }
        let _ = app;
    });
}
