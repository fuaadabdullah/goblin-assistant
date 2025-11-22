// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod goblin_runtime;
mod ipc;

use goblin_runtime::{start_runtime, stop_runtime, status, send_event};
use ipc::{get_goblins, get_providers, get_provider_models, get_stats, get_history, get_cost_summary, parse_orchestration, execute_orchestration, store_api_key, get_api_key, clear_api_key, set_provider_api_key, execute_task};
use std::sync::Arc;

/// A lightweight manager that will own runtime-related resources.
/// For now this is a placeholder; later it can hold child process handles,
/// napi-rs bindings, logging handles, sockets, etc.
#[derive(Clone)]
pub struct GoblinRuntimeManager {
    // placeholder for real runtime resources
    pub name: String,
    pub child_process: Option<std::sync::Arc<std::sync::Mutex<Option<tokio::process::Child>>>>,
}

impl GoblinRuntimeManager {
    pub fn new() -> Self {
        GoblinRuntimeManager {
            name: "goblin-runtime-manager".into(),
            child_process: None,
        }
    }
}

// IPC commands live in `src/ipc.rs` and forward to goblin_runtime.

fn main() {
    let manager = Arc::new(GoblinRuntimeManager::new());

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(manager)
        .setup(|app| {
            let _window = tauri::WindowBuilder::new(app, "main")
                .title("Goblin Assistant")
                .inner_size(1200.0, 800.0)
                .min_inner_size(800.0, 600.0)
                .center()
                .build()?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // existing runtime control commands
            start_runtime,
            stop_runtime,
            send_event,
            status,
            // new IPC commands
            get_goblins,
            get_providers,
            get_provider_models,
            get_stats,
            get_history,
            get_cost_summary,
            parse_orchestration,
            store_api_key,
            get_api_key,
            clear_api_key,
            set_provider_api_key,
            execute_orchestration,
            execute_task
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
