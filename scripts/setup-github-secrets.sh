#!/usr/bin/env bash
set -euo pipefail

# Script to add repository secrets using the GitHub CLI (gh)
# Usage: ./scripts/setup-github-secrets.sh <owner> <repo>

OWNER=${1:-}
REPO=${2:-}

if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  echo "Usage: $0 <owner> <repo>\nExample: $0 fuaadabdullah goblin-assistant"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI not found. Install from https://cli.github.com/"
  exit 1
fi

read -p "Render API Key (RENDER_API_KEY) [press Enter to skip]: " RENDER_API_KEY
read -p "Render Staging Service ID (RENDER_SERVICE_ID_STAGING) [press Enter to skip]: " RENDER_SERVICE_ID_STAGING
read -p "Render Prod Service ID (RENDER_SERVICE_ID_PROD) [press Enter to skip]: " RENDER_SERVICE_ID_PROD
read -p "GitHub Token for workflows (GITHUB_TOKEN) [press Enter to skip]: " GITHUB_TOKEN

set_secret() {
  local name=$1
  local value=$2
  if [ -n "$value" ]; then
    echo "Setting secret: $name"
    gh secret set "$name" -b"$value" -R "$OWNER/$REPO"
  else
    echo "Skipping secret: $name (empty)"
  fi
}

set_secret "RENDER_API_KEY" "$RENDER_API_KEY"
set_secret "RENDER_SERVICE_ID_STAGING" "$RENDER_SERVICE_ID_STAGING"
set_secret "RENDER_SERVICE_ID_PROD" "$RENDER_SERVICE_ID_PROD"
set_secret "GITHUB_TOKEN" "$GITHUB_TOKEN"

echo "All requested secrets processed. Verify in the repository settings UI if needed."

exit 0
