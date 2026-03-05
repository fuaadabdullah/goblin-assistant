# Kamatera Provider Setup Guide

This guide will help you configure and set up the Ollama and llama.cpp providers on Kamatera servers for your Goblin Assistant backend.

## 🎯 Overview

The Kamatera providers are:
- **Ollama (Kamatera)**: `ollama_kamatera` - Local Ollama instance on Kamatera
- **llama.cpp (Kamatera)**: `llamacpp_kamatera` - Local llama.cpp instance on Kamatera

Both are currently showing as "Unhealthy" because they need proper configuration.

## 📋 Current Status

From the health check, your Kamatera providers are configured with these default endpoints:
- **Ollama (Kamatera)**: `http://45.61.60.3:8002`
- **llama.cpp (Kamatera)**: `http://45.61.60.3:8000`

## 🚀 Quick Setup

### Option 1: Use the Automated Script

Run the configuration script:
```bash
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant
./configure_kamatera.sh
```

This script will:
1. Ask for your Kamatera server IP addresses
2. Test connectivity to the servers
3. Update the `providers.toml` configuration
4. Set environment variables

### Option 2: Manual Configuration

#### Step 1: Set Up Kamatera Servers

**For Ollama on Kamatera:**
```bash
# SSH to your Kamatera server
ssh root@your-kamatera-ip

# Install Docker
apt-get update && apt-get install -y docker.io docker-compose

# Run Ollama
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Pull models you want to use
docker exec ollama ollama pull phi3:3.8b
docker exec ollama ollama pull gemma:2b
docker exec ollama ollama pull qwen2.5:3b
```

**For llama.cpp on Kamatera:**
```bash
# SSH to your Kamatera server
ssh root@your-kamatera-ip

# Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j$(nproc)

# Download a model
wget https://huggingface.co/TheBloke/phi-3-mini-4k-instruct-gguf/resolve/main/phi-3-mini-4k-instruct.Q4_K_M.gguf

# Run llama.cpp server
./server -m phi-3-mini-4k-instruct.Q4_K_M.gguf -c 4096 --port 8000
```

#### Step 2: Update Configuration

Edit `config/providers.toml`:
```toml
[providers.ollama_kamatera]
name = "Ollama (Kamatera)"
endpoint = "http://your-kamatera-ip:11434"  # Update this
capabilities = ["chat", "reasoning", "code", "embedding"]
models = [
  "phi3:3.8b",
  "gemma:2b",
  "qwen2.5:3b",
  "deepseek-coder:1.3b",
  "mistral:7b",
]
priority_tier = 0
cost_score = 0.0
default_timeout_ms = 30000
bandwidth_score = 0.8
supports_cot = false

[providers.llamacpp_kamatera]
name = "llama.cpp (Kamatera)"
endpoint = "http://your-kamatera-ip:8000"  # Update this
capabilities = ["chat", "reasoning", "code"]
models = [
  "phi-3-mini-4k-instruct-q4",
  "llama-2-7b-chat-q4_k_m",
  "mistral-7b-instruct-v0.2-q4_k_m",
]
priority_tier = 0
cost_score = 0.0
default_timeout_ms = 30000
bandwidth_score = 0.9
supports_cot = false
```

#### Step 3: Set Environment Variables

```bash
# Set Kamatera server URLs
flyctl secrets set \
    KAMATERA_SERVER1_URL="http://your-kamatera-ip:11434" \
    KAMATERA_SERVER2_URL="http://your-kamatera-ip:8000"
```

#### Step 4: Deploy

```bash
# Deploy the updated configuration
flyctl deploy --verbose

# Test the providers
curl https://goblin-backend.fly.dev/health
```

## 🔧 Advanced Configuration

### Firewall Settings

Ensure your Kamatera server firewall allows connections:

**For Ollama (port 11434):**
```bash
ufw allow from any to any port 11434
```

**For llama.cpp (port 8000):**
```bash
ufw allow from any to any port 8000
```

### Model Management

**Add more models to Ollama:**
```bash
docker exec ollama ollama pull llama2:7b
docker exec ollama ollama pull codellama:34b
```

**Add more models to llama.cpp:**
```bash
# Download more models from Hugging Face
wget https://huggingface.co/TheBloke/llama-2-7b-chat-gguf/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

### Performance Tuning

**For Ollama:**
```bash
# Run with GPU acceleration
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Set memory limits
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --memory=8g --name ollama ollama/ollama
```

**For llama.cpp:**
```bash
# Run with GPU acceleration (if available)
./server -m model.gguf -c 4096 --port 8000 --gpu-layers 1000

# Optimize for your CPU
./server -m model.gguf -c 4096 --port 8000 -t $(nproc)
```

## 🧪 Testing Kamatera Providers

After setup, test your Kamatera providers:

```bash
# Test health check
curl https://goblin-backend.fly.dev/health

# Expected output should show:
# "Ollama (Kamatera)": {"status": "healthy", ...}
# "llama.cpp (Kamatera)": {"status": "healthy", ...}

# Test chat completion with Kamatera provider
curl -X POST "https://goblin-backend.fly.dev/chat/completions" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello from Kamatera!"}],
    "model": "phi3:3.8b"
  }'
```

## 🆘 Troubleshooting

### Provider Still Showing as Unhealthy

1. **Check connectivity:**
   ```bash
   curl -I http://your-kamatera-ip:11434
   curl -I http://your-kamatera-ip:8000
   ```

2. **Check server status:**
   ```bash
   # For Ollama
   docker ps | grep ollama
   
   # For llama.cpp
   ps aux | grep llama
   ```

3. **Check firewall:**
   ```bash
   ufw status
   ```

4. **Check logs:**
   ```bash
   # For Ollama
   docker logs ollama
   
   # For llama.cpp
   # Check the terminal where you ran the server
   ```

### Common Issues

**Issue**: `Connection refused`
**Solution**: Ensure services are running and ports are open

**Issue**: `Timeout`
**Solution**: Check network connectivity and firewall settings

**Issue**: `Model not found`
**Solution**: Pull the required models to your Kamatera server

**Issue**: `Authentication required`
**Solution**: Configure API keys if required by your setup

## 📊 Performance Monitoring

Monitor your Kamatera providers:

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://your-kamatera-ip:11434

# Monitor resource usage
htop  # On your Kamatera server

# Check model loading
docker exec ollama ollama list
```

## 🎉 Success Criteria

Your Kamatera providers are successfully configured when:

1. ✅ Health check shows "healthy" status
2. ✅ Chat completions work with local models
3. ✅ Response times are acceptable (< 5 seconds)
4. ✅ No errors in application logs
5. ✅ Models load and respond correctly

---

**Once configured, your Kamatera providers will provide fast, local AI inference without API costs!**
