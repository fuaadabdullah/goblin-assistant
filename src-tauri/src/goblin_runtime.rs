use std::sync::Arc;
mod config;
use serde::{Deserialize, Serialize};
use chrono::Utc;
use tokio::sync::Mutex;
use tokio::process::{Command, Child};
use tokio::io::AsyncWriteExt;
use serde_json::{Value as JsonValue, json};
use tauri::Emitter;
use keyring::{Entry, Result as KeyringResult};

#[derive(Serialize, Deserialize, Clone)]
pub struct RuntimeStatus {
    pub running: bool,
    pub version: String,
    pub uptime: Option<u64>,
}

#[derive(Clone)]
struct RuntimeState {
    running: bool,
    child_process: Option<Arc<Mutex<Child>>>,
}

use lazy_static::lazy_static;
mod memory;
mod cost_estimator;

lazy_static! {
    static ref RUNTIME_STATE: Mutex<RuntimeState> = Mutex::new(RuntimeState {
        running: false,
        child_process: None,
    });
}

// Secure API key storage using system keyring
fn get_keyring_entry(provider: &str) -> KeyringResult<Entry> {
    Entry::new("goblinos-desktop", provider)
}

async fn store_api_key_secure(provider: &str, key: &str) -> Result<(), String> {
    let entry = get_keyring_entry(provider)
        .map_err(|e| format!("Failed to create keyring entry: {}", e))?;

    entry.set_password(key)
        .map_err(|e| format!("Failed to store API key: {}", e))?;

    println!("Securely stored API key for provider: {}", provider);
    Ok(())
}

async fn get_api_key_secure(provider: &str) -> Result<Option<String>, String> {
    let entry = get_keyring_entry(provider)
        .map_err(|e| format!("Failed to create keyring entry: {}", e))?;

    match entry.get_password() {
        Ok(password) => Ok(Some(password)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(format!("Failed to retrieve API key: {}", e)),
    }
}

async fn clear_api_key_secure(provider: &str) -> Result<(), String> {
    let entry = get_keyring_entry(provider)
        .map_err(|e| format!("Failed to create keyring entry: {}", e))?;

    match entry.delete_password() {
        Ok(()) => {
            println!("Cleared API key for provider: {}", provider);
            Ok(())
        },
        Err(keyring::Error::NoEntry) => {
            // Key doesn't exist, which is fine
            println!("API key for provider {} was not found (already cleared)", provider);
            Ok(())
        },
        Err(e) => Err(format!("Failed to clear API key: {}", e)),
    }
}

async fn spawn_goblin_runtime() -> Result<Child, String> {
    // Find the goblin-runtime package directory
    // Allow overriding with GOBLIN_RUNTIME_DIR env var; otherwise look for common locations
    let runtime_dir = if let Ok(dir) = std::env::var("GOBLIN_RUNTIME_DIR") {
        std::path::PathBuf::from(dir)
    } else {
        let cwd = std::env::current_dir().map_err(|e| format!("Failed to get current dir: {}", e))?;
        let candidates = vec![
            cwd.join("packages").join("goblin-runtime"),
            cwd.join("goblin-runtime"),
        ];

        // Pick the first that exists
        let mut found = None;
        for c in candidates {
            if c.exists() {
                found = Some(c);
                break;
            }
        }

        match found {
            Some(p) => p,
            None => {
                return Err("Goblin runtime directory not found. Set GOBLIN_RUNTIME_DIR or place goblin-runtime in ./packages or ./goblin-runtime".to_string());
            }
        }
    };

    // Determine goblins.yaml path and pass it to the runtime via GOBLINOS_CONFIG.
    // Also, pass GOBLIN_PROJECT_ROOT so the spawned runtime knows the project
    // root (useful for demo projects not stored in the monorepo).
    let goblins_cfg = match config::find_goblins_config() {
        Ok(path) => path.to_string_lossy().to_string(),
        Err(_) => String::new(),
    };

    // Spawn the Node.js process
    let mut cmd = Command::new("node");
    if !goblins_cfg.is_empty() {
        cmd.env("GOBLINOS_CONFIG", goblins_cfg.clone());

        // If we can determine the goblins.yaml's parent directory, pass it as
        // GOBLIN_PROJECT_ROOT to the child runtime as well.
        if let Some(parent) = std::path::Path::new(&goblins_cfg).parent() {
            if let Some(p) = parent.to_str() {
                cmd.env("GOBLIN_PROJECT_ROOT", p.to_string());
            }
        }
    }

    let child = cmd
        .arg("-e")
        .arg(r#"
            const { GoblinRuntime } = require('./dist/index.js');
            const runtime = new GoblinRuntime();

            // Handle stdin messages
            process.stdin.on('data', async (data) => {
                try {
                    const message = JSON.parse(data.toString().trim());
                    let result;

                    switch (message.method) {
                        case 'listGoblins':
                            result = runtime.listGoblins();
                            break;
                        case 'getGoblinStats':
                            result = runtime.getGoblinStats(message.goblinId);
                            break;
                        case 'getGoblinHistory':
                            result = runtime.getGoblinHistory(message.goblinId, message.limit);
                            break;
                        case 'executeTask':
                            result = await runtime.executeTask(message.task);
                            break;
                        default:
                            throw new Error(`Unknown method: ${message.method}`);
                    }

                    process.stdout.write(JSON.stringify({ id: message.id, result }) + '\n');
                } catch (error) {
                    process.stdout.write(JSON.stringify({
                        id: message.id || 'unknown',
                        error: error.message
                    }) + '\n');
                }
            });

            // Signal ready
            process.stdout.write(JSON.stringify({ ready: true }) + '\n');
        "#)
    .current_dir(&runtime_dir)
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
    .spawn()
        .map_err(|e| format!("Failed to spawn goblin runtime: {}", e))?;

    Ok(child)
}

async fn send_message_to_runtime(message: serde_json::Value) -> Result<serde_json::Value, String> {
    // Get the child process without holding the lock across await points
    let child_arc = {
        let state = RUNTIME_STATE.lock().await;
        if !state.running {
            return Err("Runtime is not running".to_string());
        }
        state.child_process.as_ref().cloned().ok_or("No child process available")?
    };

    // Clone the message for sending
    let message_str = message.to_string() + "\n";

    // Send message to child process
    {
        let mut child = child_arc.lock().await;
        if let Some(stdin) = child.stdin.as_mut() {
            stdin.write_all(message_str.as_bytes()).await
                .map_err(|e| format!("Failed to write to child stdin: {}", e))?;
            stdin.flush().await
                .map_err(|e| format!("Failed to flush child stdin: {}", e))?;
        } else {
            return Err("Child process stdin not available".to_string());
        }
    }

    // Read response from child process stdout
    // For now, we'll use a simple approach - read a line and parse JSON
    // In a real implementation, you'd want more robust message framing
    use tokio::io::{AsyncBufReadExt, BufReader};

    let mut child = child_arc.lock().await;
    if let Some(stdout) = child.stdout.as_mut() {
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();

        // Read lines until we get a valid JSON response
        loop {
            line.clear();
            let bytes_read = reader.read_line(&mut line).await
                .map_err(|e| format!("Failed to read from child stdout: {}", e))?;

            if bytes_read == 0 {
                return Err("Child process stdout closed unexpectedly".to_string());
            }

            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            // Try to parse as JSON
            match serde_json::from_str::<JsonValue>(trimmed) {
                Ok(response) => {
                    // Check if this is an error response
                    if let Some(error) = response.get("error") {
                        return Err(error.as_str().unwrap_or("Unknown error").to_string());
                    }
                    // Return the result field if present, otherwise the whole response
                    return Ok(response.get("result").unwrap_or(&response).clone());
                }
                Err(_) => {
                    // Not valid JSON, continue reading
                    continue;
                }
            }
        }
    } else {
        return Err("Child process stdout not available".to_string());
    }
}

#[tauri::command]
pub async fn start_runtime() -> Result<String, String> {
    // Check if already running
    {
        let state = RUNTIME_STATE.lock().await;
        if state.running {
            return Ok("Runtime is already running".to_string());
        }
    }

    println!("Starting goblin runtime...");

    match spawn_goblin_runtime().await {
        Ok(child) => {
            let mut state = RUNTIME_STATE.lock().await;
            state.child_process = Some(Arc::new(Mutex::new(child)));
            state.running = true;
            println!("Goblin runtime started successfully");
            Ok("Runtime started".to_string())
        }
        Err(e) => {
            println!("Failed to start goblin runtime: {}", e);
            Err(e)
        }
    }
}

#[tauri::command]
pub async fn stop_runtime() -> Result<String, String> {
    let child_arc = {
        let mut state = RUNTIME_STATE.lock().await;

        if !state.running {
            return Ok("Runtime is not running".to_string());
        }

        state.child_process.take()
    };

    if let Some(child_arc) = child_arc {
        // Kill the child process outside of the lock
        let mut child = child_arc.lock().await;
        let _ = child.kill().await;
        println!("Child process killed");
    }

    {
        let mut state = RUNTIME_STATE.lock().await;
        state.running = false;
        state.child_process = None;
    }

    println!("Runtime stopped");
    Ok("Runtime stopped".to_string())
}

#[tauri::command]
pub async fn send_event(event: String) -> Result<String, String> {
    let state = RUNTIME_STATE.lock().await;
    if !state.running {
        return Err("Runtime is not running".to_string());
    }

    // TODO: Implement actual event sending logic
    println!("Received event: {}", event);

    Ok(format!("Event '{}' processed", event))
}

#[tauri::command]
pub async fn status() -> Result<RuntimeStatus, String> {
    let state = RUNTIME_STATE.lock().await;
    Ok(RuntimeStatus {
        running: state.running,
        version: "0.1.0".to_string(),
        uptime: None,
    })
}

// --- Non-command helpers for the main process to call ---
// These are simple stubs for now and should be replaced with
// actual integration with the goblin-runtime (child process, napi, etc.)

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct GoblinStats {
    pub id: String,
    pub status: String,
    pub last_seen: Option<u64>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct HistoryEntry {
    pub ts: u64,
    pub message: String,
}

pub async fn list_goblins_impl() -> Result<Vec<String>, String> {
    let message = json!({
        "id": "list_goblins",
        "method": "listGoblins"
    });

    let response = send_message_to_runtime(message).await?;

    // Parse the response as an array of strings
    match response {
        JsonValue::Array(arr) => {
            let mut goblins = Vec::new();
            for item in arr {
                if let Some(goblin_id) = item.as_str() {
                    goblins.push(goblin_id.to_string());
                }
            }
            Ok(goblins)
        }
        _ => Err(format!("Unexpected response format: {:?}", response))
    }
}

pub async fn get_goblin_stats_impl(goblin_id: &str) -> Result<GoblinStats, String> {
    let message = json!({
        "id": format!("stats_{}", goblin_id),
        "method": "getGoblinStats",
        "goblinId": goblin_id
    });

    let response = send_message_to_runtime(message).await?;

    // Parse the response as GoblinStats
    match response {
        JsonValue::Object(obj) => {
            let id = obj.get("id")
                .and_then(|v| v.as_str())
                .unwrap_or(goblin_id)
                .to_string();
            let status = obj.get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown")
                .to_string();
            let last_seen = obj.get("lastSeen")
                .and_then(|v| v.as_u64());

            Ok(GoblinStats {
                id,
                status,
                last_seen,
            })
        }
        _ => Err(format!("Unexpected response format for goblin stats: {:?}", response))
    }
}

pub async fn get_history_impl(goblin_id: &str, limit: Option<usize>) -> Result<Vec<HistoryEntry>, String> {
    let message = json!({
        "id": format!("history_{}", goblin_id),
        "method": "getGoblinHistory",
        "goblinId": goblin_id,
        "limit": limit.unwrap_or(10)
    });
    match send_message_to_runtime(message).await {
        Ok(response) => {
            // Parse the response as an array of HistoryEntry
            match response {
                JsonValue::Array(arr) => {
                    let mut history = Vec::new();
                    for item in arr {
                        if let Some(obj) = item.as_object() {
                            let ts = obj.get("ts")
                                .and_then(|v| v.as_u64())
                                .unwrap_or(0);
                            let message = obj.get("message")
                                .and_then(|v| v.as_str())
                                .unwrap_or("")
                                .to_string();

                            history.push(HistoryEntry { ts, message });
                        }
                    }
                    Ok(history)
                }
                _ => Err(format!("Unexpected response format for history: {:?}", response))
            }
        }
        Err(_) => {
            // Fallback to in-memory store for demo simplicity
            let entries = memory::get_history(goblin_id, limit).await;
            let mut history = Vec::new();
            for (ts, message) in entries {
                history.push(HistoryEntry { ts, message });
            }
            Ok(history)
        }
    }
}

fn get_system_prompt(task: &str) -> &'static str {
    match task {
        "document this code" => "You are an expert technical writer. Add clear, concise comments to the following code. Then, generate a markdown block with the function signature, a description of what it does, its parameters, and what it returns.",
        "write a unit test" => "You are an expert software engineer specializing in testing. Write a simple, effective unit test for the following code using the Jest framework. Provide only the code block for the test.",
        _ => "You are a helpful AI assistant. Provide clear and accurate responses.",
    }
}

pub async fn execute_task_impl(app: tauri::AppHandle, goblin_id: &str, task: &str, args: Option<JsonValue>) -> Result<String, String> {
    // Determine system prompt based on task
    let system_prompt = get_system_prompt(task);

    let message = json!({
        "id": format!("task_{}_{}", goblin_id, task),
        "method": "executeTask",
        "task": {
            "goblin": goblin_id,
            "task": task,
            "system_prompt": system_prompt,
            "context": args
        }
    });

    // Send the task execution message
    let response = send_message_to_runtime(message).await?;

    // Extract task ID from response if available
    let task_id = match response {
        JsonValue::Object(ref obj) => {
            obj.get("taskId")
                .and_then(|v| v.as_str())
                .unwrap_or(&format!("task_{}_{}", goblin_id, task))
                .to_string()
        }
        _ => format!("task_{}_{}", goblin_id, task)
    };

    // Start streaming simulation based on the actual response
    let task_id_for_closure = task_id.clone();
    let app_clone = app.clone();
    let goblin_id = goblin_id.to_string();
    let task = task.to_string();
    let args = args.clone();

    tokio::spawn(async move {
        let task_id_clone = task_id_for_closure;
        // Simulate streaming output chunks based on the response
        let chunks = match response {
            JsonValue::Object(ref obj) => {
                obj.get("chunks")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.len())
                    .unwrap_or(5)
            }
            _ => 5
        };

        // Identify provider and model from args for cost estimation
        let provider_name = args.as_ref().and_then(|a| a.get("provider")).and_then(|v| v.as_str()).map(|s| s.to_string());
        let model_name = args.as_ref().and_then(|a| a.get("model")).and_then(|v| v.as_str()).map(|s| s.to_string());

        for i in 0..chunks {
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
            let chunk_text = format!("Chunk {} for task {} on {}", i, task, goblin_id);
            let token_count = cost_estimator::estimate_tokens_from_text(&chunk_text);
            let provider_for_calc = provider_name.clone().unwrap_or_else(|| "unknown".to_string());
            let cost_delta = cost_estimator::estimate_cost(&provider_for_calc, model_name.clone().as_deref(), token_count);

            let payload = json!({
                "taskId": task_id_clone,
                "chunk": chunk_text,
                "progress": i as f32 / (chunks - 1) as f32,
                "provider": provider_for_calc,
                "cost_delta": cost_delta,
                "token_count": token_count
            });
            let _ = app_clone.emit("task-stream", payload);
        }

        // Emit final result
        let total_cost: f64 = (0..chunks).map(|i| {
            // approximate each chunk token length used; reuse chunk text logic from above
            let chunk_text = format!("Chunk {} for task {} on {}", i, task, goblin_id);
            let token_count = cost_estimator::estimate_tokens_from_text(&chunk_text);
            cost_estimator::estimate_cost(&provider_name.clone().unwrap_or_else(|| "unknown".to_string()), model_name.clone().as_deref(), token_count)
        }).sum();
        let result = json!({
            "taskId": task_id_clone,
            "goblin": goblin_id,
            "task": task,
            "args": args,
            "result": response,
            "provider": provider_name,
            "cost": total_cost
        });
        let _ = app_clone.emit("task-stream", result);
    });

    Ok(task_id)
}

// --- API Key Management Functions ---

pub async fn store_api_key_impl(provider: &str, key: &str) -> Result<(), String> {
    store_api_key_secure(provider, key).await
}

pub async fn get_api_key_impl(provider: &str) -> Result<Option<String>, String> {
    get_api_key_secure(provider).await
}

pub async fn clear_api_key_impl(provider: &str) -> Result<(), String> {
    clear_api_key_secure(provider).await
}

pub async fn set_provider_api_key_impl(provider: &str, key: &str) -> Result<(), String> {
    // For now, this is the same as store_api_key
    // In the future, this could have different logic for provider-specific handling
    store_api_key_impl(provider, key).await
}

pub async fn get_providers_impl() -> Result<Vec<String>, String> {
    // Return available providers, with Ollama first for out-of-the-box experience
    // TODO: This could query the goblin-runtime for available providers
    Ok(vec![
        "ollama".to_string(),
        "openai".to_string(),
        "anthropic".to_string(),
        "gemini".to_string(),
        "deepseek".to_string(),
    ])
}

pub async fn get_provider_models_impl(provider: &str) -> Result<Vec<String>, String> {
    // Return models for the given provider
    // TODO: This could query the goblin-runtime for actual available models
    match provider {
        "openai" => Ok(vec![
            "gpt-4".to_string(),
            "gpt-4-turbo".to_string(),
            "gpt-3.5-turbo".to_string(),
        ]),
        "anthropic" => Ok(vec![
            "claude-3-opus".to_string(),
            "claude-3-sonnet".to_string(),
            "claude-3-haiku".to_string(),
        ]),
        "gemini" => Ok(vec![
            "gemini-pro".to_string(),
            "gemini-pro-vision".to_string(),
        ]),
        "ollama" => Ok(vec![
            "llama2".to_string(),
            "codellama".to_string(),
            "mistral".to_string(),
        ]),
        "deepseek" => Ok(vec![
            "deepseek-chat".to_string(),
            "deepseek-coder".to_string(),
        ]),
        _ => Ok(vec![]),
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct OrchestrationStepResult {
    pub id: String,
    pub goblin: String,
    pub task: String,
    pub status: String,
    pub result: Option<JsonValue>,
    pub started_at: Option<u64>,
    pub completed_at: Option<u64>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct OrchestrationPlanResult {
    pub id: String,
    pub description: String,
    pub steps: Vec<OrchestrationStepResult>,
    pub created_at: u64,
    pub status: String,
}

/// Execute a plan by parsing a very small subset of orchestration syntax.
/// This is a pragmatic fallback: split on THEN and treat tokens as sequential steps.
pub async fn execute_orchestration_impl(app: tauri::AppHandle, text: &str, default_goblin: Option<String>) -> Result<JsonValue, String> {
    let now = chrono::Utc::now().timestamp_millis() as u64;
    let mut steps: Vec<OrchestrationStepResult> = vec![];

    let default_goblin_id = default_goblin.unwrap_or_else(|| "websmith".to_string());

    // Very naive parser: split by 'THEN'
    let tokens: Vec<&str> = text.split("THEN").map(|s| s.trim()).filter(|s| !s.is_empty()).collect();
    for (idx, token) in tokens.iter().enumerate() {
        // If token contains ':', assume goblinId: task
        let (goblin, task) = if let Some(pos) = token.find(":") {
            (
                token[..pos].trim().to_string(),
                token[pos + 1..].trim().to_string(),
            )
        } else {
            (default_goblin_id.clone(), token.to_string())
        };

        let id = format!("plan_step_{}_{}", now, idx);
        steps.push(OrchestrationStepResult {
            id: id.clone(),
            goblin: goblin.clone(),
            task: task.clone(),
            status: "pending".to_string(),
            result: None,
            started_at: None,
            completed_at: None,
        });
    }

    let mut plan = OrchestrationPlanResult {
        id: format!("plan_{}", now),
        description: text.to_string(),
        steps: steps.clone(),
        created_at: now,
        status: "pending".to_string(),
    };

    // Execute steps sequentially and update statuses
    for step in plan.steps.iter_mut() {
        step.status = "running".to_string();
        step.started_at = Some(chrono::Utc::now().timestamp_millis() as u64);
        // Execute the task via existing IPC implementation
        match execute_task_impl(app.clone(), &step.goblin, &step.task, None).await {
            Ok(task_id) => {
                step.status = "completed".to_string();
                step.result = Some(json!({ "taskId": task_id }));
                step.completed_at = Some(chrono::Utc::now().timestamp_millis() as u64);
            }
            Err(e) => {
                step.status = "failed".to_string();
                step.result = Some(json!({ "error": e }));
                step.completed_at = Some(chrono::Utc::now().timestamp_millis() as u64);
                // Continue execution - or break? For now, continue.
            }
        }
    }

    plan.status = if plan.steps.iter().any(|s| s.status == "failed") { "failed".to_string() } else { "completed".to_string() };

    Ok(json!(plan))
}

/// Parse orchestration text into an OrchestrationPlanResult JSON without executing.
/// This is intentionally similar to `execute_orchestration_impl` but does not start
/// any tasks — it only returns the parsed plan so the UI can display a preview.
pub async fn parse_orchestration_impl(text: &str, default_goblin: Option<String>) -> Result<JsonValue, String> {
    let now = chrono::Utc::now().timestamp_millis() as u64;
    let default_goblin_id = default_goblin.unwrap_or_else(|| "websmith".to_string());

    let tokens: Vec<&str> = text.split("THEN").map(|s| s.trim()).filter(|s| !s.is_empty()).collect();
    let mut steps: Vec<OrchestrationStepResult> = vec![];
    for (idx, token) in tokens.iter().enumerate() {
        let (goblin, task) = if let Some(pos) = token.find(":") {
            (
                token[..pos].trim().to_string(),
                token[pos + 1..].trim().to_string(),
            )
        } else {
            (default_goblin_id.clone(), token.to_string())
        };

        let id = format!("plan_step_{}_{}", now, idx);
        steps.push(OrchestrationStepResult {
            id: id.clone(),
            goblin: goblin.clone(),
            task: task.clone(),
            status: "pending".to_string(),
            result: None,
            started_at: None,
            completed_at: None,
        });
    }

    let plan = OrchestrationPlanResult {
        id: format!("plan_{}", now),
        description: text.to_string(),
        steps: steps.clone(),
        created_at: now,
        status: "pending".to_string(),
    };

    Ok(json!(plan))
}

/// Estimate cost for orchestration execution without actually running it
pub async fn estimate_cost_impl(orchestration_text: &str, code_input: Option<&str>, provider: Option<&str>) -> Result<JsonValue, String> {
    // Parse the orchestration to get steps
    let plan_result = parse_orchestration_impl(orchestration_text, Some("code-writer".to_string())).await?;
    let plan: OrchestrationPlanResult = serde_json::from_value(plan_result)
        .map_err(|e| format!("Failed to parse plan: {}", e))?;

    let mut total_cost = 0.0;
    let mut step_costs = Vec::new();

    // Estimate cost for each step
    for step in &plan.steps {
        // Estimate tokens based on task + code input
        let task_tokens = estimate_tokens_from_text(&step.task);
        let code_tokens = code_input.map(|c| estimate_tokens_from_text(c)).unwrap_or(0);
        let total_tokens = task_tokens + code_tokens;

        // Get cost per token for the provider
        let provider_name = provider.unwrap_or("openai");
        let cost_per_token = cost_estimator::cost_per_token(provider_name, None);

        // Estimate output tokens (assume 2x input for most tasks)
        let estimated_output_tokens = total_tokens * 2;
        let step_cost = (total_tokens + estimated_output_tokens) as f64 * cost_per_token;

        total_cost += step_cost;

        step_costs.push(json!({
            "stepId": step.id,
            "goblin": step.goblin,
            "task": step.task,
            "estimatedCost": step_cost,
            "tokenEstimate": total_tokens
        }));
    }

    Ok(json!({
        "totalCost": total_cost,
        "stepCosts": step_costs,
        "currency": "USD",
        "provider": provider.unwrap_or("openai")
    }))
}

// Simple token estimation (rough approximation)
fn estimate_tokens_from_text(text: &str) -> usize {
    // Rough estimate: ~4 characters per token for English text
    let char_count = text.chars().count();
    ((char_count as f64) / 4.0).ceil() as usize
}
