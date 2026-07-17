use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};

struct ServerProcess(Mutex<Option<Child>>);

impl Drop for ServerProcess {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(ref mut child) = *guard {
                println!("Shutting down server (PID: {})...", child.id());
                let _ = child.kill();
                let _ = child.wait();
                println!("Server stopped.");
            }
        }
    }
}

fn start_server() -> Option<Child> {
    let paths = [
        std::env::current_dir().ok().map(|p| p.join("server.py")),
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("../../../server.py"))),
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("server.py"))),
    ];

    for path in paths.into_iter().flatten() {
        if path.exists() {
            println!("Starting server: {}", path.display());
            match Command::new("python3").arg(&path).spawn() {
                Ok(child) => {
                    println!("Server started (PID: {})", child.id());
                    return Some(child);
                }
                Err(e) => {
                    eprintln!("Failed to start server: {}", e);
                    return None;
                }
            }
        }
    }
    eprintln!("server.py not found in any expected location");
    None
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::init())
        .manage(ServerProcess(Mutex::new(None)))
        .setup(|app| {
            // Window: set min size, handle close-to-tray
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_min_size(Some(tauri::LogicalSize::new(800, 600)));
                let win = window.clone();

                // Close → hide to tray instead of quitting
                window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = win.hide();
                    }
                });
            }

            // System tray
            let show_item = MenuItem::with_id(app, "show", "Show/Hide Window", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit", true, Some("CmdOrCtrl+Q"))?;
            let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

            // Use a minimal embedded RGBA icon (1x1 transparent)
            let icon = tauri::image::Image::new(&[0, 0, 0, 0], 1, 1);

            TrayIconBuilder::new()
                .icon(icon)
                .menu(&menu)
                .tooltip("Subtitle Forge")
                .on_menu_event(|app, event| {
                    match event.id().as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                if window.is_visible().unwrap_or(false) {
                                    let _ = window.hide();
                                } else {
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            }
                        }
                        "quit" => {
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { .. } = event {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;

            // Start the Python backend server
            let child = start_server();
            let state = app.state::<ServerProcess>();
            *state.0.lock().unwrap() = child;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Subtitle Forge");
}
