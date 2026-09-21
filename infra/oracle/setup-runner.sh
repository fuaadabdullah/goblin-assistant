#!/usr/bin/env bash
# infra/oracle/setup-runner.sh
#
# Installs a GitHub Actions self-hosted runner on the Oracle ARM64 VM.
# Run once after provisioning. Idempotent — safe to re-run.
#
# What this achieves:
#   The CI workflow currently builds ARM64 images via QEMU on ubuntu-latest
#   (slow, ~20-30 min for the first build). With a self-hosted runner:
#     - build-arm64 runs natively on the VM (4-5 min instead of 20-30)
#     - The deploy job no longer needs SSH from CI — it runs on-VM directly
#     - GHCR still stores the immutable image; rollback is still "pull + restart"
#
# To activate after setup:
#   1. Change build-arm64 in ci.yml: runs-on: [self-hosted, linux, arm64]
#   2. Change deploy in deploy-prod.yml: runs-on: [self-hosted, linux, arm64]
#      and remove the appleboy/ssh-action step — replace with direct shell commands.
#
# Usage:
#   ./infra/oracle/setup-runner.sh \
#     --repo     owner/goblin-assistant \
#     --token    RUNNER_REGISTRATION_TOKEN \
#     --name     oracle-arm64
#
# Get a fresh registration token from:
#   https://github.com/OWNER/goblin-assistant/settings/actions/runners/new
# Tokens expire after 1 hour. The runner uses ACTIONS_RUNNER_TOKEN (long-lived)
# after the first registration — you only need this once per reinstall.

set -euo pipefail

# ── argument parsing ──────────────────────────────────────────────────────────
REPO=""
TOKEN=""
RUNNER_NAME="oracle-arm64"
RUNNER_VERSION="2.321.0"  # pin; update when GitHub releases a new version
INSTALL_DIR="$HOME/actions-runner"
LABELS="self-hosted,linux,arm64"

usage() {
  echo "Usage: $0 --repo owner/repo --token REGISTRATION_TOKEN [--name NAME]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)  REPO="$2";         shift 2 ;;
    --token) TOKEN="$2";        shift 2 ;;
    --name)  RUNNER_NAME="$2";  shift 2 ;;
    *)       usage ;;
  esac
done

[[ -n "$REPO"  ]] || usage
[[ -n "$TOKEN" ]] || usage

# ── system dependencies ───────────────────────────────────────────────────────
echo "==> Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  curl \
  tar \
  libicu-dev \
  libssl-dev \
  ca-certificates \
  docker.io \
  docker-compose-plugin

# Add ubuntu user to docker group so the runner can call docker without sudo.
sudo usermod -aG docker ubuntu || true

# ── download runner ───────────────────────────────────────────────────────────
echo "==> Downloading GitHub Actions runner ${RUNNER_VERSION} (linux/arm64)..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

RUNNER_ARCHIVE="actions-runner-linux-arm64-${RUNNER_VERSION}.tar.gz"
RUNNER_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_ARCHIVE}"

if [[ ! -f "$RUNNER_ARCHIVE" ]]; then
  curl -fsSL -o "$RUNNER_ARCHIVE" "$RUNNER_URL"
fi

tar xzf "$RUNNER_ARCHIVE" --overwrite

# ── configure ─────────────────────────────────────────────────────────────────
echo "==> Configuring runner for https://github.com/${REPO} ..."
./config.sh \
  --url "https://github.com/${REPO}" \
  --token "$TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$LABELS" \
  --work "$INSTALL_DIR/_work" \
  --unattended \
  --replace

# ── install as systemd service ────────────────────────────────────────────────
echo "==> Installing as systemd service (svc.sh install)..."
sudo ./svc.sh install ubuntu
sudo ./svc.sh start

echo ""
echo "Runner registered and started."
echo ""
echo "Verify:  sudo systemctl status actions.runner.*.service"
echo "Logs:    sudo journalctl -u actions.runner.*.service -f"
echo ""
echo "==> Next steps to go fully native:"
echo ""
echo "  1. In ci.yml, change build-arm64 and build-arm64-sandbox to:"
echo "       runs-on: [self-hosted, linux, arm64]"
echo "     and remove the QEMU setup steps (no longer needed)."
echo ""
echo "  2. In deploy-prod.yml, change the deploy job to:"
echo "       runs-on: [self-hosted, linux, arm64]"
echo "     Replace the appleboy/ssh-action step with direct shell:"
echo "       - name: Pull and restart"
echo "         run: |"
echo "           cd ~/goblin-assistant/infra/oracle"
echo "           sed -i \"s|^GOBLIN_IMAGE=.*|GOBLIN_IMAGE=\$GOBLIN_IMAGE|\" .env"
echo "           docker compose pull api celery-worker"
echo "           docker compose up -d --no-build --remove-orphans"
echo ""
echo "  3. Ensure the runner's service user has docker group membership."
echo "     (Already done above for 'ubuntu'; re-login if docker fails.)"
