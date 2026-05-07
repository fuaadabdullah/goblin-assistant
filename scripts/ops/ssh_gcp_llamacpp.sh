#!/bin/bash

# GCP LlamaCPP Server SSH and Diagnostic Script
echo "🔐 Connecting to GCP LlamaCPP Server..."
echo "========================================"
echo ""

GCP_IP="34.132.226.143"
PORT="8000"

# Try common SSH methods
echo "Attempting SSH connection..."
echo ""
echo "Method 1: Direct SSH (if you have the key configured)"
echo "Command: ssh -i ~/.ssh/google_compute_engine $GCP_IP"
echo ""

# Provide diagnostic commands to run once connected
cat << 'EOF' > /tmp/llama_cpp_check.sh
#!/bin/bash
echo "=========================================="
echo "🔍 LlamaCPP Server Diagnostics"
echo "=========================================="
echo ""

echo "1️⃣ Checking if llama.cpp process is running..."
ps aux | grep -i llama | grep -v grep
if [ $? -eq 0 ]; then
    echo "✅ Found llama.cpp process"
else
    echo "❌ No llama.cpp process found"
fi
echo ""

echo "2️⃣ Checking what's listening on port 8000..."
sudo netstat -tlnp | grep 8000 || echo "❌ Nothing listening on port 8000"
echo ""

echo "3️⃣ Checking with lsof..."
sudo lsof -i :8000 || echo "❌ Port 8000 not in use"
echo ""

echo "4️⃣ Checking systemd service (if exists)..."
sudo systemctl status llama-cpp 2>/dev/null || sudo systemctl status llamacpp 2>/dev/null || echo "⚠️  No systemd service found"
echo ""

echo "5️⃣ Looking for llama.cpp binary..."
which llama-server || which llama-cpp-server || which server || echo "⚠️  Binary not in PATH"
find /opt /usr/local /home -name "*llama*server*" -type f 2>/dev/null | head -5
echo ""

echo "6️⃣ Checking GCP firewall (requires gcloud)..."
gcloud compute firewall-rules list --filter="allowed[]:8000" 2>/dev/null || echo "⚠️  Run: gcloud compute firewall-rules list"
echo ""

echo "=========================================="
echo "🔧 Quick Fixes:"
echo "=========================================="
echo ""
echo "To start llama.cpp server manually:"
echo "  cd /path/to/llama.cpp"
echo "  ./server --host 0.0.0.0 --port 8000 --model /path/to/model.gguf"
echo ""
echo "To create firewall rule:"
echo "  gcloud compute firewall-rules create allow-llama-cpp \\"
echo "    --allow tcp:8000 \\"
echo "    --source-ranges 0.0.0.0/0"
echo ""
echo "To enable and start systemd service (if exists):"
echo "  sudo systemctl enable llama-cpp"
echo "  sudo systemctl start llama-cpp"
echo ""
EOF

chmod +x /tmp/llama_cpp_check.sh

echo "📋 Diagnostic script created at: /tmp/llama_cpp_check.sh"
echo ""
echo "─────────────────────────────────────────"
echo "🚀 SSH Connection Options:"
echo "─────────────────────────────────────────"
echo ""
echo "Option 1: Using gcloud (recommended):"
echo "  gcloud compute ssh USERNAME@llama-cpp-instance --zone=ZONE"
echo ""
echo "Option 2: Direct SSH with key:"
echo "  ssh -i ~/.ssh/google_compute_engine USERNAME@$GCP_IP"
echo ""
echo "Option 3: Standard SSH:"
echo "  ssh USERNAME@$GCP_IP"
echo ""
echo "─────────────────────────────────────────"
echo "📝 Once connected, run these commands:"
echo "─────────────────────────────────────────"
echo ""
echo "# Copy and paste this diagnostic script:"
cat /tmp/llama_cpp_check.sh
echo ""
echo "─────────────────────────────────────────"
echo ""
echo "Attempting connection now..."
echo ""

# Try to get GCP instance info if gcloud is available
if command -v gcloud &> /dev/null; then
    echo "🔍 Looking for GCP instances with this IP..."
    gcloud compute instances list --filter="networkInterfaces[].accessConfigs[].natIP=$GCP_IP" --format="table(name,zone,status)" 2>/dev/null
    echo ""
fi

# Attempt connection (will prompt for method if multiple available)
echo "Attempting SSH connection to $GCP_IP..."
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $GCP_IP 'bash -s' < /tmp/llama_cpp_check.sh 2>/dev/null

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Connection failed. Please try manually with one of the options above."
    echo ""
    echo "Common issues:"
    echo "  - SSH key not configured"
    echo "  - Wrong username"
    echo "  - Need to use gcloud compute ssh instead"
    echo "  - Server not running or firewall blocking SSH (port 22)"
fi
