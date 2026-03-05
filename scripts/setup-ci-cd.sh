#!/bin/bash
# Goblin Assistant CI/CD Setup Script
# This script helps set up the complete CI/CD pipeline

set -e

echo "🚀 Setting up Goblin Assistant CI/CD Pipeline..."
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d ".github" ]; then
    echo "❌ Please run this script from the goblin-assistant app root directory"
    echo "   cd apps/goblin-assistant && ./scripts/setup-ci-cd.sh"
    exit 1
fi

echo "📦 Installing dependencies..."
npm ci

echo ""
echo "🔧 Setting up Husky Git hooks..."
# Initialize husky if not already done
if [ ! -d ".husky" ]; then
    npx husky install
fi

# Ensure pre-commit hook exists
if [ ! -f ".husky/pre-commit" ]; then
    echo "Creating pre-commit hook..."
    npx husky add .husky/pre-commit "npx lint-staged && npm run validate-env"
fi

# Ensure pre-push hook exists
if [ ! -f ".husky/pre-push" ]; then
    echo "Creating pre-push hook..."
    cat > .husky/pre-push << 'EOF'
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

echo "🔍 Running pre-push validation..."
npm run lint
npm run type-check
npm run test
echo "✅ Pre-push validation passed!"
EOF
    chmod +x .husky/pre-push
fi

echo ""
echo "🧪 Running initial quality checks..."
echo "Running lint check..."
npm run lint

echo "Running type check..."
npm run type-check

echo "Running tests..."
npm run test

echo "Running build..."
npm run build

echo ""
echo "🔒 Setting up branch protection..."
echo "Note: Branch protection requires GitHub CLI and repository admin access"
echo "Run this command manually after authenticating with GitHub CLI:"
echo "  ./scripts/setup-branch-protection.sh"

echo ""
echo "📋 CI/CD Setup Complete! 🎉"
echo ""
echo "📚 What was configured:"
echo "  ✅ GitHub Actions CI/CD workflow"
echo "  ✅ Pre-commit hooks (lint-staged)"
echo "  ✅ Pre-push validation (lint + type-check + tests)"
echo "  ✅ Branch protection setup script"
echo "  ✅ Comprehensive documentation"
echo ""
echo "🔄 Next Steps:"
echo "1. Push your changes to trigger the CI pipeline"
echo "2. Set up branch protection (requires admin access)"
echo "3. Configure deployment secrets if needed"
echo "4. Review the CI/CD documentation: docs/CI_CD_SETUP.md"
echo ""
echo "📖 Documentation: docs/CI_CD_SETUP.md"
echo "🔧 Branch Protection: ./scripts/setup-branch-protection.sh"
