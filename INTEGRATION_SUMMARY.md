---
description: "INTEGRATION_SUMMARY"
---

# GoblinOS Desktop - Multi-Provider Integration Summary

**Date:** November 2025

**Status:** Backend Complete ✅  |  Frontend UI WIRED ✅ — Migration Gap Closed

---

## Overview (migration gap CLOSED ✅)

The Tauri/Rust backend implementing multi-provider support, streaming, orchestration
parsing, and cost tracking is complete and tested. The React UI in
`desktop/src/` has been fully wired to the new TypeScript bindings and Tauri
commands. Operators can now access all new capabilities from the desktop app.

This document summarizes the completed frontend wiring, verification steps,
and provides code examples for future maintenance.

What was fixed (completed ✅):

- ✅ Wire the new `tauri-commands` bindings into core UI flows (`executeTask`,
  streaming helpers, `getProviders`, `getCostSummary`, `parseOrchestration`).
- ✅ Add a streaming UI component that listens for `stream-token` events and
  renders tokens progressively.
- ✅ Create a provider selector and cost summary panel that calls `getProviders()`
  and `getCostSummary()` and shows model-level breakdowns.
- ✅ Hook the orchestration editor/preview to `parseOrchestration()` and display the
  returned `OrchestrationPlan` visually.

Priority: All core features now available to operators. Streaming + provider selection
(high impact) completed first, followed by cost summary and orchestration preview.

---

## Architecture

### Provider System

**Trait-based abstraction** (`src-tauri/src/providers/mod.rs`):
```rust
pub trait ModelProvider: Send + Sync {
    async fn generate(&self, prompt: &str, system: Option<&str>)
        -> Result<GenerateResponse>;
    async fn generate_stream(&self, prompt: &str, system: Option<&str>)
        -> Result<Stream<StreamChunk>>;
    fn provider_name(&self) -> &str;
}
```

**Four implementations**:

- `OllamaProvider` - Local LLMs (default: qwen2.5:3b) - **Always available**
- `OpenAIProvider` - GPT-4/3.5 (requires `OPENAI_API_KEY`)
- `AnthropicProvider` - Claude 3.5 (requires `ANTHROPIC_API_KEY`)
- `GeminiProvider` - Gemini Pro/Flash (requires `GEMINI_API_KEY`)

**Dynamic initialization** in `GoblinRuntime::new()`:

- Ollama always initialized (localhost:11434)
- Cloud providers only if API keys present in environment

### Streaming Architecture

**Backend flow**:

1. Frontend calls `execute_task({ goblin, task, streaming: true })`
2. Backend calls `provider.generate_stream()`
3. For each `StreamChunk`, emit Tauri event: `app_handle.emit("stream-token", chunk)`
4. Frontend listens with `onStreamToken(callback)`
5. Tokens displayed progressively

**Types**:
```rust
pub struct StreamChunk {
    pub content: String,
    pub done: bool,
}
```

### Orchestration System

**Syntax examples**:

```text
"build THEN test AND lint THEN deploy"
"scraper: fetch data THEN analyzer: process IF_SUCCESS"
"task1 AND task2 AND task3"
"build THEN test IF passing THEN deploy"
```

**Parser** (`src-tauri/src/orchestration.rs`):

- Splits by " THEN " (sequential) and " AND " (parallel)
- Parses conditionals: `IF_SUCCESS`, `IF_FAILURE`, `IF_CONTAINS("value")`
- Extracts goblin IDs: `"goblin_id: task description"`
- Calculates dependencies and parallel batches
- Validates syntax (no leading operators, no consecutive operators)

**Output**: `OrchestrationPlan` with steps, dependencies, metadata

### Cost Tracking

**Pricing table** (per 1K tokens):

| Provider | Model | Input | Output |
|----------|-------|-------|--------|
| OpenAI | GPT-4 | $0.03 | $0.06 |
| OpenAI | GPT-4-turbo | $0.01 | $0.03 |
| OpenAI | GPT-3.5-turbo | $0.0005 | $0.0015 |
| Anthropic | Claude-3.5-Sonnet | $0.003 | $0.015 |
| Anthropic | Claude-3-Opus | $0.015 | $0.075 |
| Gemini | Pro | $0.00125 | $0.005 |
| Gemini | Flash | $0.000075 | $0.0003 |
| Ollama | (all models) | $0.0 | $0.0 |

**Tracking**:

- Integrated into `execute_task` - records costs per task
- `get_cost_summary` returns total_cost, cost_by_provider, cost_by_model
- Stored in `CostTracker` in `GoblinRuntime`

---

## New Tauri Commands

### Core Commands (Enhanced)

**`get_goblins()`**

- Returns: `Vec<GoblinStatus>` from goblins.yaml
- Unchanged from previous version

**`get_providers()`** ⭐ NEW

- Returns: `Vec<String>` - Available providers (e.g., `["ollama", "openai"]`)
- Only includes providers with API keys configured

**`execute_task(request: ExecuteRequest)`** ⭐ ENHANCED

- Supports streaming: `{ goblin, task, streaming: true }`
- Returns: `GoblinResponse` with cost, model, duration_ms
- Emits `"stream-token"` events if streaming enabled

### Cost Commands

**`get_cost_summary()`** ⭐ NEW

- Returns: `CostSummary` with total_cost, cost_by_provider, cost_by_model
- Aggregates all recorded tasks

### Orchestration Commands

**`parse_orchestration(text: String, default_goblin?: String)`** ⭐ NEW

- Returns: `OrchestrationPlan` with steps, dependencies, batches
- Validates syntax, extracts goblin IDs, calculates parallel depth

---

## TypeScript Bindings

Created `src/types/tauri-commands.ts` with:

### Types

- `GoblinStatus`, `ExecuteRequest`, `GoblinResponse`
- `StreamEvent`, `TaskCost`, `CostSummary`
- `OrchestrationStep`, `OrchestrationPlan`

### Functions

```typescript
// Core
getGoblins(): Promise<GoblinStatus[]>
getProviders(): Promise<string[]>
executeTask(request: ExecuteRequest): Promise<GoblinResponse>

// Streaming
onStreamToken(callback: (event: StreamEvent) => void)
executeTaskStreaming(goblin, task, onToken) // Helper

// Costs
getCostSummary(): Promise<CostSummary>
formatCost(cost: number): string // "$0.000123"
getCostColor(cost: number): string // Tailwind class

// Orchestration
parseOrchestration(text, defaultGoblin): Promise<OrchestrationPlan>
```

---

## Usage Examples

### 1. Streaming Execution

**Frontend (TypeScript)**:
```typescript
import { executeTaskStreaming } from './types/tauri-commands';

const response = await executeTaskStreaming(
  'codesmith',
  'Write a React component',
  (token) => {
    console.log(token); // Incremental tokens
    displayToken(token); // Update UI progressively
  }
);
```

**Backend (Rust)**: Automatically handled via `streaming: true` flag.

### 2. Cost Tracking

**Frontend**:
```typescript
import { getCostSummary, formatCost } from './types/tauri-commands';

const summary = await getCostSummary();
console.log(`Total: ${formatCost(summary.total_cost)}`);
console.log(`OpenAI: ${formatCost(summary.cost_by_provider.openai)}`);
console.log(`GPT-4: ${formatCost(summary.cost_by_model['gpt-4'])}`);
```

### 3. Orchestration Parsing

**Frontend**:
```typescript
import { parseOrchestration } from './types/tauri-commands';

const plan = await parseOrchestration(
  'build THEN test AND lint THEN deploy IF_SUCCESS',
  'codesmith'
);

console.log(`Total steps: ${plan.metadata.total_steps}`);
console.log(`Parallel batches: ${plan.metadata.parallel_batches}`);
plan.steps.forEach(step => {
  console.log(`${step.id}: ${step.task} (deps: ${step.dependencies})`);
});
```

### 4. Provider Selection

**Environment setup**:
```bash
# Enable OpenAI
export OPENAI_API_KEY=sk-...

# Enable Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Enable Gemini
export GEMINI_API_KEY=AIza...

# Run app
TMPDIR=/tmp npm run dev
```

**Check available providers**:
```typescript
const providers = await getProviders();
// Returns: ["ollama", "openai", "anthropic", "gemini"]
```

---

## File Structure

```text
src-tauri/
├── Cargo.toml                    # Added: regex = "1.10", chrono serde feature
├── src/
│   ├── main.rs                   # Updated: Register 7 commands (was 4)
│   ├── commands.rs               # REFACTORED: Multi-provider, streaming, costs
│   ├── commands_old.rs           # Backup of original commands
│   ├── config.rs                 # Unchanged: YAML goblin loading
│   ├── memory.rs                 # Unchanged: SQLite persistence
│   ├── cost_tracker.rs           # NEW: CostTracker with pricing tables
│   ├── orchestration.rs          # NEW: OrchestrationParser
│   └── providers/
│       ├── mod.rs                # NEW: ModelProvider trait, common types
│       ├── ollama.rs             # NEW: OllamaProvider with streaming
│       ├── openai.rs             # NEW: OpenAIProvider (GPT-4)
│       ├── anthropic.rs          # NEW: AnthropicProvider (Claude 3.5)
│       └── gemini.rs             # NEW: GeminiProvider (Gemini Pro)

desktop/
└── src/
    └── types/
        └── tauri-commands.ts     # NEW: TypeScript bindings for all commands
```

---

## Testing

### Backend Testing (Rust)

**Build check**:
```bash
cd GoblinOS/desktop/src-tauri
cargo check
```

**Run tests** (orchestration, cost tracker):
```bash
cargo test
```

**Expected output**:

```text
test orchestration::tests::test_simple_sequential ... ok
test orchestration::tests::test_parallel_tasks ... ok
test orchestration::tests::test_conditional ... ok
test cost_tracker::tests::test_cost_calculation ... ok
test cost_tracker::tests::test_summary ... ok
test cost_tracker::tests::test_free_models ... ok
```

### Manual Testing (Dev Server)

**Start dev server**:
```bash
cd GoblinOS/desktop
TMPDIR=/tmp npm run dev
```

**Test commands in Tauri devtools**:

1. **Get providers** (Ollama only by default):

```javascript
await __TAURI__.invoke('get_providers')
// Expected: ["ollama"]
```

1. **Get goblins**:

```javascript
await __TAURI__.invoke('get_goblins')
```

1. **Execute task** (non-streaming):

```javascript
const response = await __TAURI__.invoke('execute_task', {
  request: { goblin: 'codesmith', task: 'Hello', streaming: false }
});
console.log(response.reasoning);
console.log(response.cost); // Should be null for Ollama (free)
```

1. **Execute task** (streaming):

```javascript
// Listen for tokens
await window.__TAURI__.event.listen('stream-token', (event) => {
  console.log('Token:', event.payload.content);
  if (event.payload.done) console.log('Done!');
});

// Execute with streaming
await __TAURI__.invoke('execute_task', {
  request: { goblin: 'codesmith', task: 'Count to 5', streaming: true }
});
```

1. **Parse orchestration**:

```javascript
const plan = await __TAURI__.invoke('parse_orchestration', {
  text: 'task1 THEN task2 AND task3',
  defaultGoblin: 'codesmith'
});
console.log(plan.steps);
console.log(plan.metadata);
```

1. **Get cost summary**:

```javascript
const summary = await __TAURI__.invoke('get_cost_summary');
console.log(summary.total_cost); // Should be 0.0 for Ollama
```

### Provider Selector & API Key Manager — Manual verification

Follow these steps to manually confirm the provider selection and secure API key flows from the desktop UI (or via the Tauri devtools):

1. Start the dev server and open the app (see "Start dev server" above).
2. In the provider dropdown (`ProviderSelector`) choose a provider. If a cloud provider is selected and not yet configured, you can add its key in the next step.
3. In the "API Keys (secure)" panel (`APIKeyManager`):

- Enter an API key in the input and click **Save**. The UI will call the Tauri command to persist the key securely.
- Click **Check** to verify a key exists (status will say "Key present" or "No key stored").
- Click **Clear** to remove the stored key and verify the status updates to "Cleared".

Optional: verify the same actions from the Tauri devtools / console:

```javascript
// Store a provider key (same command the UI uses)
await window.__TAURI__.invoke('set_provider_api_key', { provider: 'openai', key: 'sk-...' });

// Read back the stored key
await window.__TAURI__.invoke('get_api_key', { provider: 'openai' });

// Clear the stored key
await window.__TAURI__.invoke('clear_api_key', { provider: 'openai' });
```

Notes:

- Keys are stored in the Rust/Tauri runtime process (use OS-secure storage when available).
- After saving a key, restart the dev server if the runtime was initialized without that provider and you expect the provider to appear in `get_providers()`.

---

## Pending Work

### Frontend (unit/integration) — local test run

I ran the frontend test suite locally in `desktop/` with Vitest. Summary:

- Command: `pnpm test --filter @goblinos/desktop`
- Result: 4 test files, 5 tests passed. All tests green. Duration ~800ms in my environment.
- TypeScript check: `npx tsc --noEmit` - no errors reported.
- Dev server: `pnpm run dev` - compiles successfully, runs without Tauri version mismatches.

Add these to the CI pipeline if you want the repo to enforce them on push.

### Backend (Optional)

- [ ] **Execute orchestration command** - Run full orchestration plans (not just parse)
- [ ] **Retry logic** - Add exponential backoff for provider API failures
- [ ] **Rate limiting** - Track requests per provider to avoid rate limits
- [ ] **Token estimation** - Pre-calculate estimated costs before execution

### Frontend (Required)

- [x] **Wire Provider Selector & API Manager**: Integrate the existing `ProviderSelector` and `APIKeyManager` components into the main application layout so users can switch between LLM providers and manage their API keys.

  Completed (2025-11-10): Frontend wiring implemented — `APIKeyManager` refactored to accept `providers` and `selectedProvider` props, `App.tsx` updated to pass shared provider state and callback. Unit/integration tests updated and passing locally (4 files, 5 tests). TypeScript clean, dev server runs successfully.
- [x] **Implement Streaming Output**: Create and integrate a `StreamingOutput` component that listens to the `stream-token` event and displays the response from goblins token-by-token for real-time feedback.

  Completed (2025-11-10): `StreamingView` component implemented and wired in `App.tsx` for real-time token display during streaming execution.
- [x] **Build and Integrate Cost Panel**: Develop a `CostPanel` component that uses the `get_cost_summary` command to display a full breakdown of costs by provider and model, providing financial transparency.

  Completed (2025-11-10): `CostPanel` component implemented and displays cost summaries by provider and model, refreshed after task execution.
- [x] **Create Orchestration Previewer**: Implement a UI component that takes orchestration syntax (e.g., "build THEN test"), calls `parse_orchestration`, and visually displays the resulting execution plan (steps, dependencies, and batches).

  Completed (2025-11-10): `OrchestrationPreview` component implemented and displays parsed orchestration plans with batch visualization.
- [x] **Refactor Main View**: Update the main application view (`App.tsx`) to assemble all the new components (`ProviderSelector`, `StreamingOutput`, `CostPanel`, `OrchestrationPreviewer`) into a cohesive and intuitive user interface.

  Completed (2025-11-10): `App.tsx` refactored to centralize provider state and integrate all components with proper data flow.
- [ ] **Add E2E Tests**: Create end-to-end tests to validate the full workflow: selecting a provider, executing a streaming task, viewing the output, and seeing the cost update.

### Frontend wiring examples

Minimal examples showing how the React UI should call the TypeScript bindings.

1) Execute streaming with incremental tokens (already implemented by `tauri-client.executeTaskStreaming`):

```typescript
import { runtimeClient } from './api/tauri-client';

// start streaming
await runtimeClient.executeTaskStreaming(
  selectedGoblin,
  'Write a short summary',
  (token) => {
    // append token to local state
    setStreamingText((s) => s + token);
  },
  (finalResponse) => {
    setFinalResponse(finalResponse.reasoning);
    // refresh costs
    runtimeClient.getCostSummary().then(setCostSummary);
  }
);
```

1. Provider selector (presentational component):

```tsx
<ProviderSelector
  providers={providers}
  selected={selectedProvider}
  onChange={(p) => setSelectedProvider(p)}
/>
```

1. Cost panel usage:

```tsx
<CostPanel costSummary={costSummary} />
```

Those snippets are intentionally small and map directly to the components added under `desktop/src/components/`.

### Frontend Test Checklist

- [ ] **E2E tests** - Test streaming with actual Ollama
- [ ] **Multi-provider tests** - Test OpenAI/Anthropic/Gemini with API keys
- [ ] **Cost accuracy** - Verify cost calculations match provider pricing
- [ ] **Orchestration execution** - Test complex workflows end-to-end

### Production

- [ ] **API key management UI** - Store keys in secure storage (not env vars)
- [ ] **Error handling** - User-friendly messages for API failures
- [ ] **Telemetry** - Track provider usage, failure rates, latency
- [ ] **Production build** - Test release build with all providers

---

## Breaking Changes

### For Users

- ✅ **No breaking changes** - All previous commands still work
- ⚠️ **Environment variables required** for cloud providers:
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
  - Without these, only Ollama will be available

### For Developers

- ✅ `execute_task` now returns `GoblinResponse` with `cost` and `model` fields
- ✅ New `streaming` parameter in `ExecuteRequest`
- ✅ New Tauri event: `"stream-token"` emitted during streaming
- ✅ New commands: `get_providers`, `get_cost_summary`, `parse_orchestration`

---

## Dependencies

### New Rust Dependencies

```toml
regex = "1.10"              # Orchestration parsing
chrono = { version = "0.4", features = ["serde"] }  # Timestamps with serialization
```

### No New Frontend Dependencies

All TypeScript bindings use existing Tauri APIs:

- `@tauri-apps/api/core` - `invoke()`
- `@tauri-apps/api/event` - `listen()`

---

## Configuration

### Environment Variables

```bash
# Optional: OpenAI API key
export OPENAI_API_KEY=sk-...

# Optional: Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: Google Gemini API key
export GEMINI_API_KEY=AIza...

# Required for dev: Temporary directory
export TMPDIR=/tmp
```

### goblins.yaml Format (Unchanged)

```yaml
goblins:
  - id: codesmith
    name: CodeSmith
    title: Code Generation Specialist
    guild: forge-guild
    brain:
      router: ollama  # Can be: ollama, openai, anthropic, gemini
      model: qwen2.5:3b  # Model name for selected router
```

**Future enhancement**: Respect `brain.router` field to select provider per goblin.

---

## Cost Estimation

### Example Costs (per task)

- **GPT-4 (1K input, 500 output)**:

- Input: 1000 tokens × $0.03 / 1000 = $0.03
- Output: 500 tokens × $0.06 / 1000 = $0.03
- **Total: $0.06 per task**

- **Claude 3.5 Sonnet (1K input, 500 output)**:

- Input: 1000 tokens × $0.003 / 1000 = $0.003
- Output: 500 tokens × $0.015 / 1000 = $0.0075
- **Total: $0.0105 per task**

- **Gemini Flash (1K input, 500 output)**:

- Input: 1000 tokens × $0.000075 / 1000 = $0.000075
- Output: 500 tokens × $0.0003 / 1000 = $0.00015
- **Total: $0.000225 per task**

**Ollama (any usage)**:

- **Total: $0.00 per task** ✅

---

## Troubleshooting

### Ollama not available

**Error**: `Provider 'ollama' not found`

**Solution**:

```bash
# Install Ollama
brew install ollama  # macOS

# Start Ollama service
ollama serve

# Pull a model
ollama pull qwen2.5:3b
```

### OpenAI/Anthropic/Gemini not showing

**Check**:

```typescript
const providers = await getProviders();
console.log(providers); // Should include "openai", etc.
```

**If missing**:

1. Verify API key is set: `echo $OPENAI_API_KEY`
2. Restart dev server after setting env vars
3. Check console for initialization errors

### Streaming not working

**Check**:

1. Ensure `streaming: true` in request
2. Add event listener **before** calling `execute_task`
3. Check browser console for event errors
4. Verify Ollama is running (streaming requires live provider)

### Cost showing as 0.0 for OpenAI

**Check**:

1. Verify provider is OpenAI: `response.model` should be "gpt-4-turbo-preview"
2. Check token counts in response: `response.cost.input_tokens`
3. Ensure pricing table in `cost_tracker.rs` matches current OpenAI pricing

---

## Performance Notes

### Memory Usage

- Each `StreamChunk` is ~100-500 bytes
- Full response buffered in memory during streaming
- Cost history stored in memory (not persisted yet)
- `GoblinRuntime` holds all providers (minimal overhead)

### Network

- Streaming reduces perceived latency (tokens arrive immediately)
- No buffering delay for large responses
- Provider API calls are async (non-blocking)

### Optimization Opportunities

- [ ] Stream to SQLite incrementally (avoid full response in memory)
- [ ] Persist cost history to database
- [ ] Cache provider responses for repeat queries
- [ ] Use connection pooling for provider HTTP clients

---

## Security Considerations

⚠️ **API keys in environment variables** - Not secure for production:

- Keys visible in process list
- Keys not encrypted at rest
- No key rotation support

**Production recommendations**:

1. Use system keychain (macOS Keychain, Windows Credential Manager)
2. Encrypt keys with Tauri secure storage
3. Implement key rotation UI
4. Add per-goblin key selection (isolate keys by guild)

⚠️ **Provider API calls** - Server-side proxy recommended:

- Current: Frontend → Tauri → Provider API (keys in Rust process)
- Better: Frontend → Tauri → Backend Server → Provider API (keys on server)
- Benefit: Key isolation, rate limiting, caching, audit logging

---

## Credits

- **Orchestration syntax** inspired by GoblinOS CLI toolbelts
- **Provider abstraction** modeled after LangChain providers
- **Cost tracking** pricing from official provider documentation (Dec 2024)

---

## Next Steps

1. ✅ **Test backend** with Ollama (`pnpm run dev`) — done
2. ✅ **Build streaming UI** component in React — done
3. ✅ **Add cost panel** to display summary — done
4. ✅ **Add provider selector** dropdown — done
5. ✅ **Add orchestration preview** component — done
6. ⏸️ **Implement execute_orchestration** command (optional)
7. ⏸️ **Production build** and test with all providers

---

**Status**: Backend 100% complete. Frontend WIRED and integrated — migration gap closed.

**Last Updated**: 2025-11-10
**Tauri Version**: 2.9.2
**Rust Version**: 1.74+
