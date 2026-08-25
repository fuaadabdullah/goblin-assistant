#!/usr/bin/env bash
set -euo pipefail

# Master script to run the hybrid CI/CD setup helpers in order.
# Usage: ./scripts/run-full-deployment-setup.sh <owner> <repo> <vcs>
# Example: ./scripts/run-full-deployment-setup.sh fuaadabdullah goblin-assistant gh

OWNER=${1:-}
REPO=${2:-}
VCS=${3:-gh}

if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  echo "Usage: $0 <owner> <repo> [vcs: gh|bb]"
  exit 1
fi

SCRIPTS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo "1) Running hybrid CI/CD setup"
"$SCRIPTS_DIR/setup-ci-cd.sh"

echo "2) Optionally add GitHub secrets via gh CLI"
if command -v gh >/dev/null 2>&1; then
  read -p "Run GitHub secrets setup now? [y/N]: " run_gh
  if [[ "$run_gh" =~ ^[Yy]$ ]]; then
    "$SCRIPTS_DIR/setup-github-secrets.sh" "$OWNER" "$REPO"
  else
    echo "Skipping GitHub secrets setup"
  fi
else
  echo "gh CLI not found; skip automatic secrets setup. Use the UI as documented."
fi

echo "All done. Verify GitHub Secrets, CircleCI environment variables, and deployment config before pushing."

exit 0
