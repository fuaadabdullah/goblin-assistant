#!/bin/bash
# Branch Protection Setup Script for Goblin Assistant
# This script helps configure branch protection rules via GitHub CLI

set -e

echo "Setting up branch protection for Goblin Assistant..."

if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed. Install it first: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "Not authenticated with GitHub CLI. Run 'gh auth login' first."
    exit 1
fi

REPO="fuaadabdullah/goblin-assistant"

for BRANCH in main develop; do
  echo "Configuring branch protection for $BRANCH..."

  cat > /tmp/branch_protection.json << EOF_JSON
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "policy",
      "format-check",
      "security-scan",
      "lint",
      "typecheck",
      "tests-critical-coverage",
      "build"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false
}
EOF_JSON

  gh api repos/$REPO/branches/$BRANCH/protection \
    --method PUT \
    --input /tmp/branch_protection.json

done

rm -f /tmp/branch_protection.json

echo "Branch protection configured for main and develop."
echo "Required checks: policy, format-check, security-scan, lint, typecheck, tests-critical-coverage, build"
