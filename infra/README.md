# Google Cloud Platform LLM Infrastructure

This directory contains scripts and configurations for deploying local LLM servers (Ollama and LlamaCPP) on Google Cloud Platform as replacements for the Kamatera servers.

## Quick Start

### Prerequisites

1. Install Google Cloud SDK:
```bash
# macOS
brew install --cask google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

2. Authenticate and set project:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

3. Enable required APIs:
```bash
gcloud services enable compute.googleapis.com
```

### Deploy LLM Servers

```bash
# Make script executable
chmod +x gcp-llm-setup.sh

# Set your GCP project ID
export GCP_PROJECT_ID="your-project-id"

# Deploy both Ollama and LlamaCPP servers
./gcp-llm-setup.sh both

# Or deploy individually
./gcp-llm-setup.sh ollama
./gcp-llm-setup.sh llamacpp
```

## Server Specifications

### Ollama Server
- **VM Name**: `goblin-ollama-server`
- **Machine Type**: n1-standard-4 (4 vCPUs, 15GB RAM)
- **Disk**: 100GB standard persistent disk
- **Port**: 11434
- **Models**: qwen2.5, llama3.2, mistral, codellama

### LlamaCPP Server
- **VM Name**: `goblin-llamacpp-server`
- **Machine Type**: n1-standard-8 (8 vCPUs, 30GB RAM)
- **Disk**: 100GB SSD persistent disk
- **Port**: 8000
- **Model**: Qwen 2.5 7B Instruct (Q4_K_M quantization)

## Configuration

After deployment, update your `.env.local`:

```bash
# Add these lines to apps/goblin-assistant/.env.local
OLLAMA_GCP_URL=http://YOUR_OLLAMA_IP:11434
LLAMACPP_GCP_URL=http://YOUR_LLAMACPP_IP:8000
LOCAL_LLM_API_KEY=your-api-key-here
```

## Testing

Test connectivity to your servers:

```bash
# Test Ollama
curl http://YOUR_OLLAMA_IP:11434/api/tags

# Test LlamaCPP
curl http://YOUR_LLAMACPP_IP:8000/v1/models

# Test chat completion (Ollama)
curl -X POST http://YOUR_OLLAMA_IP:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:latest",
    "prompt": "Hello, how are you?",
    "stream": false
  }'

# Test chat completion (LlamaCPP)
curl -X POST http://YOUR_LLAMACPP_IP:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

## Cost Estimation

**Monthly costs (approximate):**
- Ollama VM (n1-standard-4): ~$120/month
- LlamaCPP VM (n1-standard-8): ~$240/month
- Storage (200GB): ~$8/month
- **Total: ~$368/month**

To reduce costs:
- Stop VMs when not in use: `gcloud compute instances stop VM_NAME --zone=us-central1-a`
- Use preemptible VMs (add `--preemptible` flag, ~70% cheaper but can be terminated)
- Use spot VMs with persistent disk snapshots

## Management Commands

```bash
# List instances
gcloud compute instances list

# SSH into server
gcloud compute ssh goblin-ollama-server --zone=us-central1-a
gcloud compute ssh goblin-llamacpp-server --zone=us-central1-a

# View logs
gcloud compute instances get-serial-port-output goblin-ollama-server --zone=us-central1-a

# Stop servers
gcloud compute instances stop goblin-ollama-server --zone=us-central1-a
gcloud compute instances stop goblin-llamacpp-server --zone=us-central1-a

# Start servers
gcloud compute instances start goblin-ollama-server --zone=us-central1-a
gcloud compute instances start goblin-llamacpp-server --zone=us-central1-a

# Delete servers (WARNING: This removes everything)
gcloud compute instances delete goblin-ollama-server --zone=us-central1-a
gcloud compute instances delete goblin-llamacpp-server --zone=us-central1-a
```

## Monitoring

Monitor your instances:
```bash
# CPU and memory usage
gcloud compute instances describe VM_NAME --zone=us-central1-a

# View in GCP Console
open https://console.cloud.google.com/compute/instances
```

## Adding More Models

### Ollama
SSH into the server and run:
```bash
ssh goblin-ollama-server
ollama pull <model-name>
ollama list
```

### LlamaCPP
1. SSH into the server
2. Download model to `/opt/llama.cpp/models/`
3. Update the systemd service to point to new model
4. Restart service: `sudo systemctl restart llamacpp`

## Security Best Practices

1. **Restrict firewall rules** to only your IP:
```bash
gcloud compute firewall-rules update allow-ollama \
  --source-ranges=YOUR_IP/32
```

2. **Add authentication** via API key validation in the backend

3. **Use VPC** for private networking between services

4. **Enable Cloud Armor** for DDoS protection

5. **Setup monitoring alerts** for unusual usage patterns

## Troubleshooting

### Server not responding
```bash
# Check if VM is running
gcloud compute instances describe VM_NAME --zone=us-central1-a | grep status

# View startup script logs
gcloud compute instances get-serial-port-output VM_NAME --zone=us-central1-a

# SSH and check service status
ssh VM_NAME
sudo systemctl status ollama  # or llamacpp
sudo journalctl -u ollama -f  # view logs
```

### Out of memory
- Upgrade to larger machine type
- Use GPU-enabled instances for better performance
- Switch to lighter quantized models

### Slow responses
- Increase CPU/RAM allocation
- Use SSD persistent disks
- Consider GPU instances (T4, V100, A100)
- Optimize model context window size

## Migration from Kamatera

The old Kamatera endpoints were:
- Ollama: `http://192.175.23.150:8002`
- LlamaCPP: `http://45.61.51.220:8000`

These have been replaced with GCP endpoints. Update `dispatcher_fixed.py`:

```python
"ollama_gcp": {
    "endpoint": os.getenv("OLLAMA_GCP_URL", "http://YOUR_IP:11434"),
    "invoke_path": "/api/generate",
    "api_key_env": "LOCAL_LLM_API_KEY",
},
"llamacpp_gcp": {
    "endpoint": os.getenv("LLAMACPP_GCP_URL", "http://YOUR_IP:8000"),
    "invoke_path": "/v1/chat/completions",
    "api_key_env": "LOCAL_LLM_API_KEY",
}
```
