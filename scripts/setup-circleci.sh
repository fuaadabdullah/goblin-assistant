#!/usr/bin/env bash
set -euo pipefail

# Assist with CircleCI project setup. This script will either instruct the user
# or use the CircleCI CLI (if available) to set environment variables.
# Usage: ./scripts/setup-circleci.sh <vcs> <org> <repo>
# Example: ./scripts/setup-circleci.sh gh fuaadabdullah goblin-assistant

VCS=${1:-}
ORG=${2:-}
REPO=${3:-}

if [ -z "$VCS" ] || [ -z "$ORG" ] || [ -z "$REPO" ]; then
  echo "Usage: $0 <vcs> <org> <repo>"
  echo "Example: $0 gh fuaadabdullah goblin-assistant"
  exit 1
fi

PROJECT_SLUG="$VCS/$ORG/$REPO"

echo "Preparing CircleCI setup for project: $PROJECT_SLUG"

if command -v circleci >/dev/null 2>&1; then
  echo "circleci CLI found. You can set env vars using the CLI."
  read -p "RENDER_API_KEY (press Enter to skip): " RENDER_API_KEY
  read -p "DOCKER_LOGIN (press Enter to skip): " DOCKER_LOGIN
  read -p "DOCKER_PASSWORD (press Enter to skip): " DOCKER_PASSWORD
  read -p "GITHUB_USER (press Enter to skip): " GITHUB_USER
  read -p "GITHUB_TOKEN (press Enter to skip): " GITHUB_TOKEN

  set_env() {
    local name=$1
    local value=$2
    if [ -n "$value" ]; then
      echo "Setting $name..."
      circleci env set -p "$PROJECT_SLUG" "$name" "$value"
    else
      echo "Skipping $name"
    fi
  }

  set_env "RENDER_API_KEY" "$RENDER_API_KEY"
  set_env "DOCKER_LOGIN" "$DOCKER_LOGIN"
  set_env "DOCKER_PASSWORD" "$DOCKER_PASSWORD"
  set_env "GITHUB_USER" "$GITHUB_USER"
  set_env "GITHUB_TOKEN" "$GITHUB_TOKEN"

  echo "CircleCI environment variables set (where provided)."
else
  cat <<-EOF
  The CircleCI CLI was not found. Please do the following manually:

  1. Open: https://app.circleci.com/setup/gh/$ORG
  2. Follow "Set Up Project" → choose "Use existing config"
  3. Go to Project Settings → Environment Variables
  4. Add these variables:
     - RENDER_API_KEY
     - DOCKER_LOGIN
     - DOCKER_PASSWORD
     - GITHUB_USER
     - GITHUB_TOKEN

  After adding variables, trigger a build by pushing a commit or starting a pipeline.
EOF
fi

exit 0
