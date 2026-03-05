# Quick Start: Deploying LLMs to Google Cloud

Follow these steps to move your local LLMs from Kamatera to Google Cloud Platform.

## Step 1: Setup GCP Account

1. Go to https://cloud.google.com/
2. Create a new project or select existing one
3. Enable billing for the project

## Step 2: Install Google Cloud SDK

```bash
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows
# Download from: https://cloud.google.com/sdk/docs/install
```

## Step 3: Authenticate

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable compute.googleapis.com
```

## Step 4: Deploy Servers

```bash
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant/infra

# Make script executable
chmod +x gcp-llm-setup.sh

# Set your project ID
export GCP_PROJECT_ID="your-project-id"

# Deploy both servers (takes ~10 minutes)
./gcp-llm-setup.sh both
```

The script will output IPs like:
```
✅ Ollama server created successfully!
📍 External IP: 34.123.45.67
🔗 Ollama endpoint: http://34.123.45.67:11434

✅ LlamaCPP server created successfully!
📍 External IP: 35.234.56.78
🔗 LlamaCPP endpoint: http://35.234.56.78:8000
```

## Step 5: Update Configuration

Add to `apps/goblin-assistant/.env.local`:

```bash
# GCP LLM Servers
OLLAMA_GCP_URL=http://YOUR_OLLAMA_IP:11434
LLAMACPP_GCP_URL=http://YOUR_LLAMACPP_IP:8000
LOCAL_LLM_API_KEY=your-secure-api-key-here
```

## Step 6: Test Connection

```bash
# Test Ollama
curl http://YOUR_OLLAMA_IP:11434/api/tags

# Test LlamaCPP  
curl http://YOUR_LLAMACPP_IP:8000/v1/models
```

## Step 7: Restart Backend

```bash
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Kill old backend
pkill -f "uvicorn.*8004"

# Start with new config
./start-backend-with-env.sh > /tmp/backend.log 2>&1 &

# Wait and test
sleep 5
curl http://localhost:8004/health | python3 -m json.tool
```

## Step 8: Test Chat

```bash
# Test with GCP LlamaCPP
curl -X POST http://localhost:8004/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "provider": "llamacpp_gcp",
    "model": "qwen2.5-7b-instruct"
  }'

# Test with GCP Ollama
curl -X POST http://localhost:8004/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "provider": "ollama_gcp",
    "model": "qwen2.5:latest"
  }'
```

## Cost Management

**Estimated costs:**
- Ollama VM: ~$120/month
- LlamaCPP VM: ~$240/month
- Storage: ~$8/month
- **Total: ~$368/month**

**To reduce costs:**

```bash
# Stop when not in use
gcloud compute instances stop goblin-ollama-server --zone=us-central1-a
gcloud compute instances stop goblin-llamacpp-server --zone=us-central1-a

# Start when needed
gcloud compute instances start goblin-ollama-server --zone=us-central1-a
gcloud compute instances start goblin-llamacpp-server --zone=us-central1-a

# Use preemptible VMs (70% cheaper, but can be terminated)
# Add --preemptible flag to the gcp-llm-setup.sh script
```

## Troubleshooting

### Servers not accessible

```bash
# Check firewall rules
gcloud compute firewall-rules list

# Verify servers are running
gcloud compute instances list

# Check server logs
gcloud compute instances get-serial-port-output goblin-ollama-server --zone=us-central1-a
```

### Out of memory

```bash
# Upgrade machine type
gcloud compute instances set-machine-type goblin-llamacpp-server \
  --machine-type=n1-standard-16 \
  --zone=us-central1-a
```

### Slow performance

Consider GPU instances:
```bash
# Add GPU (requires different setup)
--accelerator type=nvidia-tesla-t4,count=1
```

## Alternative: Docker Compose (Local/VM)

If you prefer Docker:

```bash
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant/infra

# Download models first (one-time)
docker-compose run model-downloader

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f ollama
docker-compose logs -f llamacpp

# Stop services
docker-compose down
```

## Next Steps

1. Monitor usage and costs in GCP Console
2. Setup CloudFlare or VPN for additional security
3. Add authentication/API keys for production
4. Setup alerts for downtime or high usage
5. Consider GPU instances for better performance

## Support

- GCP Documentation: https://cloud.google.com/compute/docs
- Ollama Docs: https://ollama.ai/docs
- LlamaCPP Docs: https://github.com/ggerganov/llama.cpp
