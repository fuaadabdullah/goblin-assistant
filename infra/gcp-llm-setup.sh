#!/bin/bash
# Google Cloud Platform - LLM Server Setup Script
# This script sets up Ollama and LlamaCPP servers on GCP
# Usage: ./gcp-llm-setup.sh [ollama|llamacpp|both]

set -e

PROJECT_ID="${GCP_PROJECT_ID:-goblin-assistant}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${GCP_ZONE:-us-central1-a}"
# Reduced cost configuration: e2-medium (2 vCPUs, 4GB RAM) with preemptible
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-medium}"  # ~$12/month with preemptible
DISK_SIZE="${GCP_DISK_SIZE:-50}"  # GB - reduced to 50GB

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Function to create and setup Ollama server
setup_ollama() {
    echo "🚀 Setting up Ollama server on GCP..."
    
    VM_NAME="goblin-ollama-server"
    
    # Create VM instance
    gcloud compute instances create "$VM_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --preemptible \
        --boot-disk-size="${DISK_SIZE}GB" \
        --boot-disk-type=pd-standard \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --tags=ollama-server,http-server \
        --metadata=startup-script='#!/bin/bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
systemctl enable ollama
systemctl start ollama

# Pull only essential models (reduced for cost)
sleep 10
ollama pull qwen2.5:3b
ollama pull llama3.2:1b

echo "✅ Ollama setup complete"
'
    
    # Create firewall rule for Ollama (port 11434)
    gcloud compute firewall-rules create allow-ollama \
        --project="$PROJECT_ID" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:11434 \
        --source-ranges=0.0.0.0/0 \
        --target-tags=ollama-server \
        || echo "Firewall rule already exists"
    
    # Get the external IP
    sleep 30
    EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
    
    echo ""
    echo "✅ Ollama server created successfully!"
    echo "📍 External IP: $EXTERNAL_IP"
    echo "🔗 Ollama endpoint: http://$EXTERNAL_IP:11434"
    echo ""
    echo "Add to your .env.local:"
    echo "OLLAMA_GCP_URL=http://$EXTERNAL_IP:11434"
}

# Function to create and setup LlamaCPP server
setup_llamacpp() {
    echo "🚀 Setting up LlamaCPP server on GCP..."
    
    VM_NAME="goblin-llamacpp-server"
    
    # Create VM instance with more resources for LlamaCPP
    gcloud compute instances create "$VM_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --machine-type="e2-standard-4" \
        --preemptible \
        --boot-disk-size="${DISK_SIZE}GB" \
        --boot-disk-type=pd-standard \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --tags=llamacpp-server,http-server \
        --metadata=startup-script='#!/bin/bash
# Install dependencies
apt-get update
apt-get install -y build-essential git cmake wget python3-pip

# Install llama.cpp
cd /opt
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make

# Create models directory
mkdir -p /opt/llama.cpp/models

# Download smaller quantized model
cd /opt/llama.cpp/models
wget https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf

# Create systemd service
cat > /etc/systemd/system/llamacpp.service << EOF
[Unit]
Description=LlamaCPP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/llama.cpp
ExecStart=/opt/llama.cpp/server -m /opt/llama.cpp/models/qwen2.5-3b-instruct-q4_k_m.gguf --host 0.0.0.0 --port 8000 -c 2048 --threads 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl daemon-reload
systemctl enable llamacpp
systemctl start llamacpp

echo "✅ LlamaCPP setup complete"
'
    
    # Create firewall rule for LlamaCPP (port 8000)
    gcloud compute firewall-rules create allow-llamacpp \
        --project="$PROJECT_ID" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:8000 \
        --source-ranges=0.0.0.0/0 \
        --target-tags=llamacpp-server \
        || echo "Firewall rule already exists"
    
    # Get the external IP
    sleep 30
    EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
    
    echo ""
    echo "✅ LlamaCPP server created successfully!"
    echo "📍 External IP: $EXTERNAL_IP"
    echo "🔗 LlamaCPP endpoint: http://$EXTERNAL_IP:8000"
    echo ""
    echo "Add to your .env.local:"
    echo "LLAMACPP_GCP_URL=http://$EXTERNAL_IP:8000"
}

# Main script logic
MODE="${1:-both}"

case "$MODE" in
    ollama)
        setup_ollama
        ;;
    llamacpp)
        setup_llamacpp
        ;;
    both)
        setup_ollama
        echo ""
        echo "⏳ Waiting 60 seconds before setting up LlamaCPP..."
        sleep 60
        setup_llamacpp
        ;;
    *)
        echo "Usage: $0 [ollama|llamacpp|both]"
        exit 1
        ;;
esac

echo ""
echo "🎉 GCP LLM server setup complete!"
echo ""
echo "Next steps:"
echo "1. Wait 5-10 minutes for the servers to fully initialize"
echo "2. Test the endpoints:"
echo "   curl http://<OLLAMA_IP>:11434/api/tags"
echo "   curl http://<LLAMACPP_IP>:8000/v1/models"
echo "3. Update your .env.local with the URLs above"
echo "4. Restart your backend: ./start-backend-with-env.sh"
