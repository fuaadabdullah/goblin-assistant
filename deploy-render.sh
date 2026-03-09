#!/bin/bash
# Canonical backend deployment helper for Render

set -e

echo "🚀 Deploying Goblin Assistant Backend to Render"
echo "================================================"

cd "$(dirname "$0")"

if [ ! -f "render.yaml" ]; then
  echo "❌ render.yaml not found in project root."
  exit 1
fi

echo "✅ Found render.yaml blueprint"
echo ""
echo "Next steps (Render dashboard):"
echo "1) Connect this repository in Render"
echo "2) Use Blueprint deploy with render.yaml"
echo "3) Set required secrets in Render Environment"
echo "4) Trigger deploy and verify /health"
echo ""
echo "Canonical backend start command: uvicorn api.main:app --host 0.0.0.0 --port \$PORT"
