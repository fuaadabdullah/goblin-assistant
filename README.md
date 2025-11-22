# Goblin Assistant

> **Enterprise-Grade AI Orchestration Platform** - A sophisticated desktop application demonstrating advanced AI routing, multi-provider failover, cost optimization, and intelligent task handling across 31+ AI providers.

[![Demo](https://img.shields.io/badge/Demo-View%20GIF-blue)](https://github.com/fuaadabdullah/goblin-assistant/releases)

## ✨ What It Does

Goblin Assistant is a production-ready AI orchestration platform that showcases enterprise-grade AI management:

### 🤖 Advanced AI Routing Engine

- **31 AI Providers**: Seamlessly routes across OpenAI, Anthropic, Google Gemini, DeepSeek, SiliconFlow, Moonshot, ZhipuAI, Baichuan, StepFun, Minimax, Alibaba Qwen, Tencent Hunyuan, SenseTime, NagaAI, H2O AI, Cloudflare Workers, Cloudflare Vectors, HuggingFace, Together AI, Replicate, and local providers (Ollama, LM Studio, llama.cpp)
- **Intelligent Provider Selection**: Multi-dimensional scoring algorithm weighing latency (40%), cost (30%), reliability (20%), and bandwidth (10%)
- **Automatic Failover**: Circuit breaker pattern with graceful degradation to local models when cloud providers fail
- **Cost Optimization**: Real-time budget tracking ($10/hour limit) with automatic fallback to cost-effective providers

### 🧠 Smart Task Processing

- **Chain-of-Thought Suppression**: Automatically suppresses verbose reasoning for simple tasks (chat, summary, translation) while enabling it for complex tasks (analysis, planning, code review)
- **Task-Aware Routing**: Different providers selected based on task type and provider capabilities
- **Streaming Responses**: Real-time token-by-token streaming with cost tracking

### 🏗️ Enterprise Architecture

- **TOML Configuration**: Human-editable provider configuration with clear separation of concerns
- **FastAPI Backend**: High-performance async routing with comprehensive metrics
- **Cross-Platform Desktop**: Tauri + React + TypeScript stack
- **Offline-First**: Works with local Ollama/LM Studio models, syncs when online

## 🚀 Key Features

### AI Provider Management

- **Dynamic Provider Discovery**: Automatically detects available providers based on API keys and local installations
- **Provider Health Monitoring**: Real-time latency tracking and success rate monitoring
- **Bandwidth Optimization**: Routes to high-bandwidth providers for large requests
- **Geographic Optimization**: Prefers local providers when available

### Intelligent Routing

- **Weighted Scoring Algorithm**: Balances speed, cost, reliability, and throughput
- **Task-Specific Optimization**: Chat tasks use fast providers, analysis tasks use reasoning-capable models
- **Cost-Aware Decisions**: Stays within budget limits, prefers free/local providers when possible
- **Circuit Breaker Protection**: Automatically isolates failing providers

### Advanced Orchestration

- **Multi-Step Workflows**: Chain AI tasks with `THEN` syntax (e.g., `docs-writer: document code THEN code-writer: write tests`)
- **Conditional Execution**: `IF_SUCCESS`, `IF_FAILURE` logic for complex workflows
- **Parallel Processing**: `AND` syntax for concurrent task execution
- **Streaming Orchestration**: Watch entire workflows execute in real-time

### Cost & Performance Monitoring

- **Real-Time Cost Tracking**: Live updates as tokens are processed across all providers
- **Performance Metrics**: Latency, throughput, and success rates per provider
- **Budget Management**: Configurable hourly/daily spending limits
- **Usage Analytics**: Detailed breakdowns by provider, model, and task type

## 🎯 What It Can Actually Do Now

### Production-Ready AI Routing

```text
✅ Route across 31 providers automatically
✅ Handle provider failures gracefully
✅ Optimize for cost, speed, and reliability
✅ Suppress CoT for simple tasks, enable for complex ones
✅ Real-time streaming with cost tracking
✅ Budget enforcement ($10/hour default)
✅ Local-first with cloud fallback (Ollama, LM Studio, llama.cpp)
✅ TOML-based configuration management
✅ Circuit breaker pattern for reliability
✅ Multi-dimensional provider scoring
✅ Task-aware provider selection
```

### Enterprise Features

```text
✅ TOML-based configuration management
✅ Circuit breaker pattern for reliability
✅ Multi-dimensional provider scoring
✅ Task-aware provider selection
✅ Comprehensive metrics and monitoring
✅ FastAPI async backend
✅ Cross-platform desktop app (Tauri + React + TypeScript)
✅ 31 provider integrations (26 cloud + 5 local)
✅ Real-time cost optimization and budget tracking
✅ Streaming orchestration with progress indicators
```

### Developer Experience

```text
✅ Paste code → Get instant documentation + tests
✅ Orchestration commands: "docs-writer THEN code-writer"
✅ Live cost tracking during execution
✅ Streaming responses with progress indicators
✅ Provider selection and health status
✅ Demo mode for consistent demonstrations
```

## 🎥 Live Demo

*Watch as the app intelligently routes across providers, optimizes costs, and executes complex AI workflows in real-time.*

## 🏗️ Technical Stack

- **Frontend**: React + TypeScript + Tailwind CSS + Tauri (Rust)
- **Backend**: FastAPI (Python async) + TOML configuration
- **AI Routing**: Custom Python engine with 31 provider integrations
- **Local AI**: Ollama, LM Studio, llama.cpp with GGUF models
- **Cloud AI**: OpenAI, Anthropic, Gemini, DeepSeek, and 26+ more APIs
- **Configuration**: TOML for human-editable settings with environment variable support
- **Persistence**: SQLite for metrics and task history
- **Build System**: Vite for development, Tauri for native packaging

## 📦 Releases

Download the latest version for your platform:

- [macOS (Intel)](https://github.com/fuaadabdullah/goblin-assistant/releases/download/v2.0.0/goblin-assistant_2.0.0_x64.dmg)
- [macOS (Apple Silicon)](https://github.com/fuaadabdullah/goblin-assistant/releases/download/v2.0.0/goblin-assistant_2.0.0_arm64.dmg)
- [Windows](https://github.com/fuaadabdullah/goblin-assistant/releases/download/v2.0.0/goblin-assistant_2.0.0_x64_en-US.msi)
- [Linux (AppImage)](https://github.com/fuaadabdullah/goblin-assistant/releases/download/v2.0.0/goblin-assistant_2.0.0_amd64.AppImage)

## � Secrets and API Keys

Do NOT commit secrets to git. Instead prefer one of the following approaches:

- Use `smithy` to manage secrets: `smithy secrets set OPENAI_API_KEY "<VALUE>"`.
- For local development, add keys to a local `.env` file (ensure `.env` is listed in `.gitignore`).
- Use SOPS for repository-level encrypted secrets in production.

See `GoblinOS/API_KEYS_MANAGEMENT.md` for longer guidance.

## �🛠️ Quick Start

### Prerequisites

1. **Install Ollama** (for free local AI):
   ```bash
   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh

   # Windows - download from https://ollama.ai/download
   ```

2. **Pull a model**:
   ```bash
   ollama pull qwen2.5:7b
   ```

3. **(Optional) Set up LM Studio** for additional local models:
   ```bash
   # Download LM Studio from https://lmstudio.ai/
   # Install and launch LM Studio
   # Download a model (e.g., Llama 2 7B Chat, Mistral 7B, etc.)
   # Start the local server in LM Studio:
   #   - Go to "Local Server" tab
   #   - Select your downloaded model
   #   - Set port to 1234 (default)
   #   - Click "Start Server"
   ```

4. **(Optional) Set up llama.cpp** for additional local models:
   ```bash
   # Clone and build llama.cpp
   git clone https://github.com/ggerganov/llama.cpp
   cd llama.cpp && mkdir build && cd build
   cmake .. -DLLAMA_METAL=on && make -j$(sysctl -n hw.ncpu)

   # Download a model (TinyLlama 1.1B for testing)
   mkdir -p models
   curl -L -o models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
     https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

   # Start server
   ./build/bin/llama-server -m models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --host 0.0.0.0 --port 8080 --threads 4
   ```

5. **(Optional) Set OpenAI API Key** for cloud AI:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

### Local LLM Setup Script

For easy setup of local LLMs, run the included setup script:

```bash
./setup-local-llm.sh
```

This script will:
- Check for Ollama installation and archived models on USB
- Start Ollama service and pull recommended models
- Check LM Studio server status and available models
- Check llama.cpp server status
- Provide configuration guidance

### Archived Ollama Models

If you have archived Ollama models on external storage, the setup script will detect them at:
- `/Volumes/Fuaad 1/Storage_Hierarchy/Development/Dependencies/ollama_old/`

The script can help integrate these models with your local Ollama installation.

### Run the App

1. **Download** the latest release from [GitHub Releases](https://github.com/fuaadabdullah/goblin-assistant/releases)
2. **Extract** and run the executable
3. **Try it out**:
   - Paste some code in the input area
   - Use the default orchestration: `docs-writer: document this code THEN code-writer: write a unit test`
   - Click **Run** and watch the magic!

   ### Development (fast iteration)

   For fast iteration, the default development environment uses Vite for the frontend and a FastAPI server for the backend. This avoids native Tauri rebuilds.

   ```bash
   # Run the FastAPI runtime and Vite web dev server concurrently (default)
   pnpm run dev:fast

   # Alternative: Run just the web dev server (requires FastAPI running separately)
   pnpm run dev:web

   # Then open http://localhost:1420 in your browser
   ```

   To run with the native Tauri shell for production-like testing (requires occasional native rebuilds):

   ```bash
   pnpm run dev:tauri
   ```

   The runtime is automatically selected based on the `VITE_GOBLIN_RUNTIME` environment variable (set in `.env`):
   - `fastapi` (default): Uses FastAPI backend for fast development iteration
   - `tauri`: Uses native Tauri backend for production builds

   ### Testing

   Run the test suite:

   ```bash
   # Unit tests
   pnpm run test

   # End-to-end tests (requires Playwright browsers)
   pnpm run e2e
   ```

   The e2e tests cover the full user flow: loading the app, entering code and orchestration commands, executing tasks with streaming output, and verifying cost tracking.

   **Note**: E2E tests require Playwright browsers to be installed (`npx playwright install`). The tests mock the runtime layer to work with both Tauri and FastAPI backends.

## 🤝 Contributing

This is a demo project focused on showcasing capabilities. For production use, see the full [GoblinOS](https://github.com/fuaadabdullah/ForgeMonorepo/tree/main/GoblinOS) monorepo.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

Built with ❤️ using GoblinOS
