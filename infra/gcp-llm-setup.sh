#!/bin/bash
# Google Cloud Platform — LLM Server Setup
# Project: goblin-assistant-489711
# Account: fuaadabdullah@gmail.com
#
# Usage:
#   ./gcp-llm-setup.sh ollama
#   ./gcp-llm-setup.sh llamacpp
#   ./gcp-llm-setup.sh both
#   ./gcp-llm-setup.sh status
#   ./gcp-llm-setup.sh delete [ollama|llamacpp|both]
#   ./gcp-llm-setup.sh start  [ollama|llamacpp|both]
#   ./gcp-llm-setup.sh stop   [ollama|llamacpp|both]

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT_ID="goblin-assistant-489711"
ACCOUNT="fuaadabdullah@gmail.com"
ZONE="us-central1-a"
REGION="us-central1"

OLLAMA_VM="goblin-ollama-server"
LLAMACPP_VM="goblin-llamacpp-server"

# e2-standard-2: 2 vCPU / 8 GB RAM — adequate for 3B models
# Spot pricing ≈ $7–9/month each
OLLAMA_MACHINE="e2-standard-2"
LLAMACPP_MACHINE="e2-standard-2"
DISK_SIZE="30"

OLLAMA_PORT="11434"
LLAMACPP_PORT="8080"

# Models
OLLAMA_MODELS=("qwen2.5:3b" "llama3.2:1b")
LLAMACPP_MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"
LLAMACPP_MODEL_FILE="qwen2.5-3b-instruct-q4_k_m.gguf"

# ── Helpers ───────────────────────────────────────────────────────────────────

log()  { echo "▸ $*"; }
ok()   { echo "✓ $*"; }
err()  { echo "✗ $*" >&2; }
die()  { err "$*"; exit 1; }

require_gcloud() {
  command -v gcloud &>/dev/null || die "gcloud not found — install from https://cloud.google.com/sdk/docs/install"
  gcloud config set account "$ACCOUNT" --quiet
  gcloud config set project "$PROJECT_ID" --quiet
}

vm_exists() {
  gcloud compute instances describe "$1" \
    --zone="$ZONE" --project="$PROJECT_ID" \
    --format="value(name)" &>/dev/null 2>&1
}

vm_status() {
  gcloud compute instances describe "$1" \
    --zone="$ZONE" --project="$PROJECT_ID" \
    --format="value(status)" 2>/dev/null || echo "MISSING"
}

vm_ip() {
  gcloud compute instances describe "$1" \
    --zone="$ZONE" --project="$PROJECT_ID" \
    --format="value(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null || echo ""
}

ensure_firewall() {
  local RULE="$1" PORT="$2" TAG="$3"
  if ! gcloud compute firewall-rules describe "$RULE" \
       --project="$PROJECT_ID" &>/dev/null 2>&1; then
    log "Creating firewall rule $RULE (tcp:$PORT)..."
    gcloud compute firewall-rules create "$RULE" \
      --project="$PROJECT_ID" \
      --direction=INGRESS \
      --priority=1000 \
      --network=default \
      --action=ALLOW \
      --rules="tcp:$PORT" \
      --source-ranges="0.0.0.0/0" \
      --target-tags="$TAG" \
      --quiet
    ok "Firewall rule $RULE created"
  else
    ok "Firewall rule $RULE already exists"
  fi
}

wait_for_http() {
  local URL="$1" MAX="${2:-120}" INTERVAL=5
  log "Waiting for $URL (up to ${MAX}s)..."
  local elapsed=0
  while [[ $elapsed -lt $MAX ]]; do
    if curl -sf --connect-timeout 3 "$URL" &>/dev/null; then
      ok "Endpoint is up: $URL"
      return 0
    fi
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
    echo -n "."
  done
  echo ""
  err "Timed out waiting for $URL"
  return 1
}

# ── Ollama ────────────────────────────────────────────────────────────────────

OLLAMA_STARTUP=$(cat <<'STARTUP_EOF'
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/startup.log) 2>&1
echo "[startup] beginning at $(date)"

# System update
apt-get update -qq
apt-get install -y -qq curl

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Configure to listen on all interfaces
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_KEEP_ALIVE=24h"
EOF

systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama

# Wait for Ollama to be ready
echo "[startup] waiting for Ollama API..."
for i in $(seq 1 30); do
  curl -sf http://localhost:11434/api/tags &>/dev/null && break
  sleep 2
done

# Pull models
echo "[startup] pulling qwen2.5:3b..."
ollama pull qwen2.5:3b

echo "[startup] pulling llama3.2:1b..."
ollama pull llama3.2:1b

echo "[startup] done at $(date)"
STARTUP_EOF
)

setup_ollama() {
  log "Setting up Ollama VM: $OLLAMA_VM"

  if vm_exists "$OLLAMA_VM"; then
    log "VM $OLLAMA_VM already exists (status: $(vm_status "$OLLAMA_VM")) — skipping create"
  else
    log "Creating $OLLAMA_VM ($OLLAMA_MACHINE, ${DISK_SIZE}GB, spot, $ZONE)..."
    gcloud compute instances create "$OLLAMA_VM" \
      --project="$PROJECT_ID" \
      --zone="$ZONE" \
      --machine-type="$OLLAMA_MACHINE" \
      --provisioning-model=SPOT \
      --instance-termination-action=STOP \
      --boot-disk-size="${DISK_SIZE}GB" \
      --boot-disk-type=pd-standard \
      --image-family=ubuntu-2204-lts \
      --image-project=ubuntu-os-cloud \
      --tags="ollama-server,http-server" \
      --metadata="startup-script=$OLLAMA_STARTUP" \
      --quiet
    ok "VM created"
  fi

  ensure_firewall "allow-ollama" "$OLLAMA_PORT" "ollama-server"

  local IP
  IP=$(vm_ip "$OLLAMA_VM")
  echo ""
  ok "Ollama VM ready"
  echo "  IP:       $IP"
  echo "  Endpoint: http://$IP:$OLLAMA_PORT"
  echo "  Note: model downloads take ~5–10 min after VM boot"
  echo ""
  echo "OLLAMA_GCP_ENDPOINT=http://$IP:$OLLAMA_PORT"
}

# ── LlamaCPP ──────────────────────────────────────────────────────────────────

LLAMACPP_STARTUP=$(cat <<STARTUP_EOF
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/startup.log) 2>&1
echo "[startup] beginning at \$(date)"

apt-get update -qq
apt-get install -y -qq build-essential cmake git wget python3-pip curl

# Build llama.cpp from source
cd /opt
git clone --depth=1 https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build -DLLAMA_CURL=ON
cmake --build build --config Release -j\$(nproc)

# Install to /usr/local/bin
install build/bin/llama-server /usr/local/bin/llama-server

# Download quantized model
mkdir -p /opt/models
echo "[startup] downloading model..."
wget -q --show-progress -O /opt/models/$LLAMACPP_MODEL_FILE \
  "$LLAMACPP_MODEL_URL"

# Systemd service
cat > /etc/systemd/system/llamacpp.service <<'SVCEOF'
[Unit]
Description=llama.cpp Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/llama-server \\
  --model /opt/models/$LLAMACPP_MODEL_FILE \\
  --host 0.0.0.0 \\
  --port $LLAMACPP_PORT \\
  --ctx-size 4096 \\
  --threads \$(nproc) \\
  --parallel 4
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable llamacpp
systemctl start llamacpp

echo "[startup] done at \$(date)"
STARTUP_EOF
)

setup_llamacpp() {
  log "Setting up LlamaCPP VM: $LLAMACPP_VM"

  if vm_exists "$LLAMACPP_VM"; then
    log "VM $LLAMACPP_VM already exists (status: $(vm_status "$LLAMACPP_VM")) — skipping create"
  else
    log "Creating $LLAMACPP_VM ($LLAMACPP_MACHINE, ${DISK_SIZE}GB, spot, $ZONE)..."
    gcloud compute instances create "$LLAMACPP_VM" \
      --project="$PROJECT_ID" \
      --zone="$ZONE" \
      --machine-type="$LLAMACPP_MACHINE" \
      --provisioning-model=SPOT \
      --instance-termination-action=STOP \
      --boot-disk-size="${DISK_SIZE}GB" \
      --boot-disk-type=pd-standard \
      --image-family=ubuntu-2204-lts \
      --image-project=ubuntu-os-cloud \
      --tags="llamacpp-server,http-server" \
      --metadata="startup-script=$LLAMACPP_STARTUP" \
      --quiet
    ok "VM created"
  fi

  ensure_firewall "allow-llamacpp" "$LLAMACPP_PORT" "llamacpp-server"

  local IP
  IP=$(vm_ip "$LLAMACPP_VM")
  echo ""
  ok "LlamaCPP VM ready"
  echo "  IP:       $IP"
  echo "  Endpoint: http://$IP:$LLAMACPP_PORT"
  echo "  Note: build + model download take ~15–20 min after VM boot"
  echo ""
  echo "LLAMACPP_GCP_ENDPOINT=http://$IP:$LLAMACPP_PORT"
}

# ── Status / Lifecycle ────────────────────────────────────────────────────────

show_status() {
  echo ""
  echo "┌─────────────────────────────────────────────────────────────┐"
  echo "│  GCP LLM Server Status  (project: $PROJECT_ID)  │"
  echo "└─────────────────────────────────────────────────────────────┘"

  for VM in "$OLLAMA_VM" "$LLAMACPP_VM"; do
    STATUS=$(vm_status "$VM")
    IP=$(vm_ip "$VM" 2>/dev/null || echo "n/a")
    echo ""
    echo "  VM:     $VM"
    echo "  Status: $STATUS"
    echo "  IP:     $IP"
    if [[ "$STATUS" == "RUNNING" && "$IP" != "n/a" ]]; then
      if [[ "$VM" == "$OLLAMA_VM" ]]; then
        MODELS=$(curl -sf --connect-timeout 3 "http://$IP:$OLLAMA_PORT/api/tags" 2>/dev/null \
          | python3 -c "import json,sys; d=json.load(sys.stdin); print(', '.join(m['name'] for m in d.get('models',[])))" 2>/dev/null || echo "unreachable")
        echo "  Models: $MODELS"
      else
        MODELS=$(curl -sf --connect-timeout 3 "http://$IP:$LLAMACPP_PORT/v1/models" 2>/dev/null \
          | python3 -c "import json,sys; d=json.load(sys.stdin); print(', '.join(m['id'] for m in d.get('data',[])))" 2>/dev/null || echo "unreachable")
        echo "  Models: $MODELS"
      fi
    fi
  done
  echo ""
}

lifecycle() {
  local ACTION="$1" TARGET="${2:-both}"
  local VMS=()
  [[ "$TARGET" == "ollama" || "$TARGET" == "both" ]] && VMS+=("$OLLAMA_VM")
  [[ "$TARGET" == "llamacpp" || "$TARGET" == "both" ]] && VMS+=("$LLAMACPP_VM")

  for VM in "${VMS[@]}"; do
    log "${ACTION^}ing $VM..."
    gcloud compute instances "$ACTION" "$VM" \
      --zone="$ZONE" --project="$PROJECT_ID" --quiet
    ok "$VM ${ACTION}ed"
  done
}

delete_vms() {
  local TARGET="${1:-both}"
  echo "WARNING: This will permanently delete VMs."
  read -rp "Type 'yes' to confirm: " CONFIRM
  [[ "$CONFIRM" == "yes" ]] || { log "Aborted."; exit 0; }
  lifecycle "delete" "$TARGET"
}

# ── SSH helpers ───────────────────────────────────────────────────────────────

ssh_vm() {
  local VM="$1"
  gcloud compute ssh "$VM" \
    --zone="$ZONE" --project="$PROJECT_ID" \
    --account="$ACCOUNT"
}

logs_vm() {
  local VM="$1"
  gcloud compute instances get-serial-port-output "$VM" \
    --zone="$ZONE" --project="$PROJECT_ID" | tail -50
}

# ── Main ──────────────────────────────────────────────────────────────────────

require_gcloud

CMD="${1:-help}"

case "$CMD" in
  ollama)   setup_ollama ;;
  llamacpp) setup_llamacpp ;;
  both)
    setup_ollama
    echo ""
    setup_llamacpp
    ;;
  status)   show_status ;;
  start)    lifecycle "start"  "${2:-both}" ;;
  stop)     lifecycle "stop"   "${2:-both}" ;;
  delete)   delete_vms "${2:-both}" ;;
  ssh-ollama)   ssh_vm  "$OLLAMA_VM" ;;
  ssh-llamacpp) ssh_vm  "$LLAMACPP_VM" ;;
  logs-ollama)  logs_vm "$OLLAMA_VM" ;;
  logs-llamacpp) logs_vm "$LLAMACPP_VM" ;;
  help|*)
    echo "Usage: $0 <command> [target]"
    echo ""
    echo "Commands:"
    echo "  both            Create both VMs (default)"
    echo "  ollama          Create Ollama VM only"
    echo "  llamacpp        Create LlamaCPP VM only"
    echo "  status          Show VM status + loaded models"
    echo "  start  [both|ollama|llamacpp]"
    echo "  stop   [both|ollama|llamacpp]"
    echo "  delete [both|ollama|llamacpp]"
    echo "  ssh-ollama / ssh-llamacpp"
    echo "  logs-ollama / logs-llamacpp"
    echo ""
    echo "Project: $PROJECT_ID  Zone: $ZONE"
    ;;
esac
