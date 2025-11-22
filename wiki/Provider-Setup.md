# Provider Setup Guide

This guide covers configuring AI providers in Goblin Assistant for optimal performance and cost management.

## Supported Providers

Goblin Assistant supports **31+ AI providers** across different categories:

### Major Cloud Providers

- **OpenAI** (GPT-4, GPT-3.5, DALL-E)
- **Anthropic** (Claude 3, Claude 2)
- **Google Gemini** (Gemini 1.5, Gemini 1.0)
- **DeepSeek** (DeepSeek Coder, Chat)

### Chinese Providers

- **SiliconFlow**, **Moonshot**, **ZhipuAI**
- **Baichuan**, **StepFun**, **Minimax**
- **Alibaba Qwen**, **Tencent Hunyuan**

### Specialized Providers

- **HuggingFace**, **Together AI**, **Replicate**
- **Cloudflare Workers AI**, **H2O AI**

### Local AI

- **Ollama** (30+ models)
- **LM Studio**
- **llama.cpp**

## 🔧 Configuration Structure

All provider configuration is stored in `config/providers.toml`:

```toml
# Provider settings
[provider_name]
enabled = true
api_key = "your-api-key-here"
base_url = "https://api.provider.com"  # Optional
timeout = 30  # seconds

# Model-specific settings
[provider_name.model_name]
priority = 100
cost_weight = 0.3
latency_weight = 0.4
reliability_weight = 0.3
max_tokens = 4096
temperature = 0.7
```

## 🚀 Quick Setup Examples

### OpenAI Configuration

```toml
[openai]
api_key = "sk-your-openai-key-here"
enabled = true
organization = "org-your-org-id"  # Optional

[openai.gpt-4]
priority = 100
cost_weight = 0.2
latency_weight = 0.4
reliability_weight = 0.4

[openai.gpt-3.5-turbo]
priority = 80
cost_weight = 0.4
latency_weight = 0.4
reliability_weight = 0.2
```

### Anthropic Configuration

```toml
[anthropic]
api_key = "sk-ant-your-anthropic-key-here"
enabled = true

[anthropic.claude-3-opus]
priority = 95
cost_weight = 0.3
latency_weight = 0.3
reliability_weight = 0.4

[anthropic.claude-3-sonnet]
priority = 90
cost_weight = 0.4
latency_weight = 0.3
reliability_weight = 0.3
```

### Local Ollama Setup

```toml
[ollama]
enabled = true
base_url = "http://localhost:11434"

[ollama.llama2:13b]
priority = 60
cost_weight = 1.0  # Free, so lowest cost priority
latency_weight = 0.2
reliability_weight = 0.8

[ollama.codellama:13b]
priority = 70
cost_weight = 1.0
latency_weight = 0.2
reliability_weight = 0.8
```

## 🔑 API Key Management

### Secure Storage

**Never commit API keys to version control!**

```bash
# Use environment variables
export OPENAI_API_KEY="sk-your-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Or create a .env file (gitignored)
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### TOML Configuration with Environment Variables

```toml
[openai]
api_key = "${OPENAI_API_KEY}"
enabled = true

[anthropic]
api_key = "${ANTHROPIC_API_KEY}"
enabled = true
```

## ⚡ Performance Tuning

### Provider Selection Weights

The routing engine uses a weighted scoring system:

- **Latency (40%)**: Response speed (lower is better)
- **Cost (30%)**: Price per token (lower is better)
- **Reliability (20%)**: Success rate (higher is better)
- **Bandwidth (10%)**: Token throughput (higher is better)

### Optimizing for Speed

```toml
[openai.gpt-3.5-turbo]
priority = 100
latency_weight = 0.6  # Favor speed
cost_weight = 0.2
reliability_weight = 0.2
max_tokens = 2048  # Smaller for faster responses
```

### Optimizing for Cost

```toml
[openai.gpt-3.5-turbo]
priority = 100
latency_weight = 0.2
cost_weight = 0.6  # Favor cost savings
reliability_weight = 0.2

[ollama.llama2:7b]
priority = 80
cost_weight = 1.0  # Free local model
latency_weight = 0.3
reliability_weight = 0.7
```

### Optimizing for Quality

```toml
[anthropic.claude-3-opus]
priority = 100
latency_weight = 0.2
cost_weight = 0.2
reliability_weight = 0.6  # Favor reliability
max_tokens = 8192
temperature = 0.1  # More deterministic
```

## 🏠 Local AI Setup

### Ollama Installation

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download

# Start service
ollama serve

# Pull models
ollama pull llama2:7b-chat
ollama pull codellama:7b
ollama pull deepseek-coder:6.7b
```

### LM Studio Setup

1. Download from [lmstudio.ai](https://lmstudio.ai)
2. Load a GGUF model
3. Start local server on port 1234
4. Configure in Goblin Assistant:

```toml
[lmstudio]
enabled = true
base_url = "http://localhost:1234"
```

## 📊 Monitoring & Health Checks

### Provider Status Monitoring

The application automatically monitors provider health:

- **Connectivity**: API endpoint availability
- **Rate Limits**: Remaining requests/quota
- **Latency**: Response time tracking
- **Success Rate**: Error rate monitoring

### Custom Health Checks

```toml
[provider.health_check]
enabled = true
interval = 60  # seconds
timeout = 10
retries = 3
```

## 🛡️ Security Best Practices

### API Key Rotation

```bash
# Rotate keys regularly
# Update environment variables
export OPENAI_API_KEY="sk-new-key-here"

# Restart the application
# Keys are loaded on startup
```

### Network Security

```toml
[security]
# Use HTTPS endpoints only
force_https = true

# Certificate validation
verify_ssl = true

# Proxy support
proxy_url = "http://proxy.company.com:8080"
```

## 🔄 Failover Configuration

### Automatic Failover

```toml
[failover]
enabled = true
max_retries = 3
backoff_factor = 2.0
fallback_to_local = true  # Use Ollama if cloud fails
```

### Provider Groups

Group providers by capability:

```toml
[groups.fast]
providers = ["openai.gpt-3.5-turbo", "anthropic.claude-3-haiku"]
max_latency = 2000  # ms

[groups.reasoning]
providers = ["openai.gpt-4", "anthropic.claude-3-opus"]
min_tokens = 4096

[groups.local]
providers = ["ollama.llama2:13b", "lmstudio"]
cost_weight = 1.0  # Always free
```

## 📈 Scaling Considerations

### High-Throughput Setup

```toml
[scaling]
concurrent_requests = 10
rate_limiting = true
burst_limit = 5

[openai]
requests_per_minute = 60
tokens_per_minute = 40000
```

### Load Balancing

```toml
[load_balancer]
strategy = "round_robin"  # or "weighted", "least_loaded"
health_check_interval = 30
failover_threshold = 0.8  # 80% success rate
```

## 🧪 Testing Configuration

### Validation Commands

```bash
# Test provider connectivity
python -m goblin_assistant.test_providers

# Validate configuration
python -m goblin_assistant.validate_config config/providers.toml

# Performance benchmark
python -m goblin_assistant.benchmark --providers openai,anthropic
```

### Sample Test Tasks

```python
# test_providers.py
test_tasks = [
    "Hello world",
    "Write a Python function to calculate fibonacci",
    "Explain quantum computing in simple terms",
    "Code review: analyze this function for bugs"
]
```

## 📚 Advanced Topics

- [Configuration Deep Dive](Configuration-Deep-Dive.md) - Advanced TOML configuration
- [Performance Optimization](Performance-Optimization.md) - Tuning for specific use cases
- [API Integration](API-Integration.md) - Custom provider integration

---

*Need help with a specific provider? Check the [Troubleshooting Guide](Troubleshooting-Guide.md) or open an [issue](https://github.com/fuaadabdullah/goblin-assistant/issues).*
