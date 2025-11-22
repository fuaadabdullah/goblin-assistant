use std::sync::Arc;

// Expose IPC commands for the frontend. Keep these small and forward to
// the goblin_runtime helper implementations.
use crate::goblin_runtime;
use crate::GoblinRuntimeManager;

#[tauri::command]
pub async fn get_goblins(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>) -> Result<Vec<String>, String> {
    goblin_runtime::list_goblins_impl().await
}

#[tauri::command]
pub async fn get_stats(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, goblin_id: String) -> Result<goblin_runtime::GoblinStats, String> {
    goblin_runtime::get_goblin_stats_impl(&goblin_id).await
}

#[tauri::command]
pub async fn get_history(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, goblin_id: String, limit: Option<usize>) -> Result<Vec<goblin_runtime::HistoryEntry>, String> {
    goblin_runtime::get_history_impl(&goblin_id, limit).await
}

#[tauri::command]
pub async fn get_providers(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>) -> Result<Vec<String>, String> {
    goblin_runtime::get_providers_impl().await
}

#[tauri::command]
pub async fn get_provider_models(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, provider: String) -> Result<Vec<String>, String> {
    goblin_runtime::get_provider_models_impl(&provider).await
}

#[tauri::command]
pub async fn get_cost_summary(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>) -> Result<serde_json::Value, String> {
    // TODO: implement cost summary
    Ok(serde_json::json!({
        "total_cost": 0.0,
        "cost_by_provider": {},
        "cost_by_model": {}
    }))
}

#[tauri::command]
pub async fn parse_orchestration(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, text: String, default_goblin: Option<String>) -> Result<serde_json::Value, String> {
    goblin_runtime::parse_orchestration_impl(&text, default_goblin).await
}

#[tauri::command]
pub async fn execute_orchestration(app: tauri::AppHandle, _mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, text: String, default_goblin: Option<String>) -> Result<serde_json::Value, String> {
    goblin_runtime::execute_orchestration_impl(app, &text, default_goblin).await
}

#[tauri::command]
pub async fn store_api_key(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, provider: String, _key: String) -> Result<(), String> {
    goblin_runtime::store_api_key_impl(&provider, &_key).await
}

#[tauri::command]
pub async fn get_api_key(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, _provider: String) -> Result<Option<String>, String> {
    goblin_runtime::get_api_key_impl(&_provider).await
}

#[tauri::command]
pub async fn clear_api_key(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, provider: String) -> Result<(), String> {
    goblin_runtime::clear_api_key_impl(&provider).await
}

#[tauri::command]
pub async fn set_provider_api_key(_mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, provider: String, _key: String) -> Result<(), String> {
    goblin_runtime::set_provider_api_key_impl(&provider, &_key).await
}

#[tauri::command]
pub async fn execute_task(app: tauri::AppHandle, _mgr: tauri::State<'_, Arc<GoblinRuntimeManager>>, goblin_id: String, task: String, args: Option<serde_json::Value>) -> Result<String, String> {
    goblin_runtime::execute_task_impl(app, &goblin_id, &task, args).await
}
