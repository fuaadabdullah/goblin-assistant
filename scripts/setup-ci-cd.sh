#!/usr/bin/env bash
# Goblin Assistant CI/CD Setup Script
# This script prepares the hybrid GitHub Actions + CircleCI workflow.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

echo "Setting up Goblin Assistant CI/CD pipeline..."
echo ""

cd "$REPO_ROOT"

if [ ! -f "Makefile" ] || [ ! -f "package.json" ] || [ ! -d ".github" ] || [ ! -d ".circleci" ]; then
  echo "Please run this script from the goblin-assistant repository root."
  exit 1
fi

echo "Installing workspace dependencies..."
make install

echo ""
echo "Running initial quality checks..."
make lint
make type-check
make check-route-lifecycle
make check-providers-json
make contract-checks
make test
make build

echo ""
echo "CircleCI setup"
read -r -p "Run CircleCI setup helper now? [y/N]: " run_circleci
if [[ "$run_circleci" =~ ^[Yy]$ ]]; then
  origin_url=$(git remote get-url origin 2>/dev/null || true)
  owner=""
  repo=""

  if [[ "$origin_url" =~ github\.com[:/]+([^/]+)/([^/]+?)(\.git)?$ ]]; then
    owner="${BASH_REMATCH[1]}"
    repo="${BASH_REMATCH[2]}"
  fi

  if [ -z "$owner" ] || [ -z "$repo" ]; then
    read -r -p "GitHub owner/org: " owner
    read -r -p "Repository name: " repo
  fi

  if [ -n "$owner" ] && [ -n "$repo" ]; then
    "$SCRIPT_DIR/setup-circleci.sh" gh "$owner" "$repo"
  else
    echo "Skipping CircleCI setup because repository coordinates were not provided."
  fi
else
  echo "Skipping CircleCI setup"
fi

echo ""
echo "Branch protection"
echo "Note: Branch protection requires GitHub CLI and repository admin access"
echo "Run this command manually after authenticating with GitHub CLI:"
echo "  ./scripts/setup-branch-protection.sh"

echo ""
echo "CI/CD setup complete."
echo ""
echo "What was configured:"
echo "  - Workspace install via Makefile"
echo "  - Repo-wide quality checks"
echo "  - Pre-commit hooks from the checked-in Husky config"
echo "  - Optional CircleCI environment setup via helper"
echo "  - Branch protection setup script"
echo "  - Hybrid CI/CD documentation"
echo ""
echo "Next steps:"
echo "1. Push your changes to trigger the CI pipeline"
echo "2. Set up branch protection (requires admin access)"
echo "3. Configure deployment secrets if needed"
echo "4. Review the CI/CD documentation: docs/infra/CI_CD_SETUP.md"
echo ""
echo "Documentation: docs/infra/CI_CD_SETUP.md"
echo "Branch protection: ./scripts/setup-branch-protection.sh"
