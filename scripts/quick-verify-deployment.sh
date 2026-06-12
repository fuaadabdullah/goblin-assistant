#!/bin/bash

# Quick Deployment Status Check
# Fast verification without blocking on long timeouts

echo "🚀 Goblin Assistant - Quick Deployment Status"
echo "=============================================="
echo ""

BACKEND_URL="https://goblin-backend-dt30.onrender.com"
FRONTEND_URL="https://goblin-assistant.vercel.app"

# Quick timeout check (3 second timeout)
echo "⏱️  Quick backend check (3s timeout)..."
if timeout 3 curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health" 2>/dev/null | grep -q "200"; then
    echo "✅ Backend responding"
else
    echo "⏳ Backend still starting (this is normal, typically 2-5 minutes)"
fi

echo ""
echo "⏱️  Quick frontend check (3s timeout)..."
if timeout 3 curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}" 2>/dev/null | grep -q "200\|301\|302"; then
    echo "✅ Frontend responding"
else
    echo "⏳ Frontend still starting (this is normal, typically 1-3 minutes)"
fi

echo ""
echo "📊 Dashboard Links:"
echo "==================="
echo ""
echo "Render Backend Dashboard:"
echo "  https://dashboard.render.com/services/goblin-backend"
echo ""
echo "Vercel Frontend Dashboard:"
echo "  https://vercel.com/dashboard/projects/goblin-assistant"
echo ""
echo "Production URLs (once ready):"
echo "  Backend: ${BACKEND_URL}"
echo "  Frontend: ${FRONTEND_URL}"
echo ""
echo "💡 Typical deployment timeline:"
echo "   • Git push to main: ✅ Complete"
echo "   • Auto-deploy trigger: ✅ Initiated"
echo "   • Backend build + start: ⏳ 2-5 minutes"
echo "   • Frontend build + deploy: ⏳ 1-3 minutes"
echo ""
echo "Next steps:"
echo "  1. Monitor dashboards above for build progress"
echo "  2. Once both show 'Live', run: npm run test:e2e"
echo "  3. Or check health: curl ${BACKEND_URL}/health"
echo ""
