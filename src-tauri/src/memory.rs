use lazy_static::lazy_static;
use std::collections::HashMap;
use tokio::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

lazy_static! {
    static ref MEMORY_STORE: Mutex<HashMap<String, Vec<(u64, String)>>> = Mutex::new(HashMap::new());
}

pub async fn add_history_entry(goblin_id: &str, message: &str) {
    let mut store = MEMORY_STORE.lock().await;
    let bucket = store.entry(goblin_id.to_string()).or_insert_with(Vec::new);
    let ts = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() as u64;
    bucket.push((ts, message.to_string()));
}

pub async fn get_history(goblin_id: &str, limit: Option<usize>) -> Vec<(u64, String)> {
    let store = MEMORY_STORE.lock().await;
    let entries = store.get(goblin_id).cloned().unwrap_or_default();
    let mut entries = entries;
    entries.reverse(); // newest first
    if let Some(l) = limit {
        entries.truncate(l);
    }
    entries
}
