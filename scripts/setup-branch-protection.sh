#!/bin/bash
# Branch Protection Setup Script for Goblin Assistant
# This script helps configure branch protection rules via GitHub CLI

set -e

echo "🛡️ Setting up branch protection for Goblin Assistant..."

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed. Please install it first:"
    echo "   https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI. Please run 'gh auth login' first."
    exit 1
fi

REPO="fuaadabdullah/forgemono"
BRANCH="main"

echo "🔧 Configuring branch protection for $BRANCH branch..."

# Create JSON payload for branch protection
cat > /tmp/branch_protection.json << EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Goblin Assistant CI/CD (lint-and-type-check)",
      "Goblin Assistant CI/CD (test)",
      "Goblin Assistant CI/CD (build)",
      "Goblin Assistant CI/CD (security-scan)",
      "Goblin Assistant CI/CD (quality-gate)"
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
EOF

# Set up branch protection with required status checks
gh api repos/$REPO/branches/$BRANCH/protection \
  --method PUT \
  --input /tmp/branch_protection.json

# Clean up temporary file
rm /tmp/branch_protection.json

if [ $? -eq 0 ]; then
    echo "✅ Branch protection configured successfully!"
    echo ""
    echo "📋 Branch Protection Rules Applied:"
    echo "  - Required status checks: lint-and-type-check, test, build, security-scan, quality-gate"
    echo "  - Require pull request reviews (1 reviewer required)"
    echo "  - Require code owner reviews"
    echo "  - Dismiss stale reviews"
    echo "  - Enforce for admins"
    echo "  - No force pushes allowed"
    echo "  - No branch deletions allowed"
else
    echo "❌ Failed to configure branch protection"
    exit 1
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Verify the branch protection rules in GitHub Settings > Branches"
echo "2. Consider adding CODEOWNERS file for automatic reviewer assignment"
echo "3. Set up repository secrets for deployment if needed"
