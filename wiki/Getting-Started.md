# Getting Started with Goblin Assistant

Welcome to Goblin Assistant! This guide will walk you through your first steps with the AI orchestration platform.

## Prerequisites

Before you begin, ensure you have:

- **Node.js 18+** and **npm** installed
- **Python 3.11+** installed
- **Git** for cloning the repository
- At least **8GB RAM** (16GB recommended for local AI models)

## 🚀 Quick Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/fuaadabdullah/goblin-assistant.git
cd goblin-assistant

# Install dependencies
npm install

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Providers

Create a `config/providers.toml` file:

```toml
[openai]
api_key = "your-openai-api-key-here"
enabled = true

[anthropic]
api_key = "your-anthropic-api-key-here"
enabled = true

# For local AI (optional but recommended)
[ollama]
enabled = true
base_url = "http://localhost:11434"
```

### 3. Start Local AI (Optional)

For offline capabilities, set up Ollama:

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2:7b-chat

# Start Ollama service
ollama serve
```

### 4. Launch the Application

```bash
# Start the backend
python api/fastapi/app.py

# In another terminal, start the frontend
npm run dev
```

## 🎯 Your First Task

1. **Open the application** in your browser (usually `http://localhost:5173`)

2. **Enter a simple task** in the input field:

   ```text
   Summarize the benefits of AI orchestration
   ```

3. **Watch the magic happen**:
   - The system automatically selects the best AI provider
   - You see real-time cost tracking
   - Response streams in token-by-token

## 🧠 Understanding the Interface

### Main Components

- **Task Input**: Where you enter your AI requests
- **Provider Status**: Shows which AI providers are available
- **Cost Tracker**: Real-time spending monitor
- **Response Area**: Where AI responses appear
- **Metrics Panel**: Performance statistics

### Key Features to Try

1. **Simple Chat**: Just type any question

2. **Code Tasks**: Ask for code reviews or generation

3. **Multi-step Tasks**: Use `THEN` for workflows

   ```text
   Write a Python function to calculate fibonacci THEN explain how it works
   ```

## 🔧 Basic Configuration

### Budget Settings

Set spending limits in `config/providers.toml`:

```toml
[budget]
hourly_limit = 10.0  # $10 per hour
daily_limit = 50.0   # $50 per day
```

### Provider Priorities

Adjust provider selection weights:

```toml
[openai.gpt-4]
priority = 100  # Higher = preferred
cost_weight = 0.3
latency_weight = 0.4
reliability_weight = 0.3
```

## 🐛 Troubleshooting First Launch

### Common Issues

**Backend won't start:**

- Check Python version: `python --version`
- Ensure virtual environment is activated
- Verify all dependencies: `pip list`

**Frontend won't load:**

- Check Node.js version: `node --version`
- Clear cache: `rm -rf node_modules/.vite`
- Try different port: `npm run dev -- --port 3000`

**No AI responses:**

- Verify API keys in `config/providers.toml`
- Check provider status in the UI
- Look at browser console for errors

### Getting Help

- Check the [Troubleshooting Guide](Troubleshooting-Guide.md)
- Open an [issue](https://github.com/fuaadabdullah/goblin-assistant/issues)
- Join [discussions](https://github.com/fuaadabdullah/goblin-assistant/discussions)

## 🎉 What's Next?

Now that you have Goblin Assistant running, explore:

- [Provider Setup](Provider-Setup.md) - Configure more AI providers
- [Basic Orchestration](Basic-Orchestration.md) - Learn task routing
- [Advanced Orchestration](Advanced-Orchestration.md) - Multi-step workflows

Happy orchestrating! 🤖✨
