---
description: "README"
---

# GoblinOS Desktop - Tauri Application

This directory contains the Tauri desktop application for GoblinOS, with a React frontend and Rust backend communicating via IPC.

## Project Structure

```
src-tauri/
├── src/
│   ├── main.rs              # Tauri application entry point
│   └── goblin_runtime.rs    # Runtime management logic
├── Cargo.toml               # Rust dependencies
└── tauri.conf.json          # Tauri configuration
```

## Architecture

- **Frontend**: React application (existing dashboard package)
- **Backend**: Rust application using Tauri
- **Communication**: IPC (Inter-Process Communication) instead of HTTP
- **Runtime Management**: Goblin runtime logic managed by Rust backend

## IPC Commands

The Rust backend exposes the following IPC commands:

- `start_runtime()` - Start the goblin runtime
- `stop_runtime()` - Stop the goblin runtime
- `send_event(event: string)` - Send an event to the runtime
- `status()` - Get runtime status

## Development Setup

### Prerequisites

- Rust (latest stable)
- Node.js and pnpm
- Tauri CLI

### Running the Application

1. **Install dependencies** (from monorepo root):
   ```bash
   pnpm install
   ```

2. **Start development server**:
   ```bash
   cd GoblinOS/desktop
   pnpm run dev
   ```

   Or from monorepo root:
   ```bash
   pnpm --filter @goblinos/desktop run dev
   ```

### Building for Production

```bash
cd GoblinOS/desktop
pnpm run build
```

## Current Status

✅ **Completed:**
- Tauri project structure created
- Rust backend with IPC commands implemented
- Basic runtime state management
- Configuration files set up

⚠️ **Known Issues:**
- Frontend dev server setup needs workspace dependency resolution
- May need to adjust build commands based on monorepo setup

## Next Steps

1. Fix frontend dev server dependencies in workspace
2. Implement actual goblin runtime logic in `goblin_runtime.rs`
3. Add proper error handling and logging
4. Integrate with existing GoblinOS components