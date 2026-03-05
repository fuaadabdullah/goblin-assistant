#!/bin/bash
# Deploy GoblinOS Assistant to Vercel (Frontend)

set -e  # Exit on error

echo "🚀 Deploying GoblinOS Assistant Frontend to Vercel..."

# Navigate to project directory
cd "$(dirname "$0")"

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Build the project
echo "📦 Building frontend..."
npm run build

# Deploy to Vercel
echo "🌐 Deploying to Vercel..."
vercel --prod

echo "✅ Frontend deployment complete!"
echo "🔗 URL: https://goblin.fuaad.ai"
echo ""
echo "Next steps:"
echo "1. Deploy backend to Fly.io (run ./deploy-fly.sh)"
echo "2. Configure environment variables in Vercel dashboard"
echo "3. Test the deployed application"
