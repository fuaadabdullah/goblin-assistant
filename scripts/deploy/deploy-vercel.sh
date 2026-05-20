#!/bin/bash
# Deploy GoblinOS Assistant to Vercel (Frontend)

set -e  # Exit on error

echo "🚀 Deploying GoblinOS Assistant Frontend to Vercel..."

# Navigate to project root (script lives in scripts/deploy)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    pnpm add -g vercel
fi

# Build the project
echo "📦 Building frontend..."
pnpm --filter @goblin/web build

# Deploy to Vercel
echo "🌐 Deploying to Vercel..."
vercel --prod

echo "✅ Frontend deployment complete!"
echo "🔗 URL: https://goblin-assistant.vercel.app"
echo ""
echo "Next steps:"
echo "1. Deploy backend to Render (run ./deploy-render.sh)"
echo "2. Configure environment variables in Vercel dashboard"
echo "3. Test the deployed application"
