#!/bin/bash

echo "🔍 GCP LlamaCPP Server Diagnostics"
echo "======================================"
echo ""

GCP_IP="34.132.226.143"
PORT="8000"

echo "📍 Target: $GCP_IP:$PORT"
echo ""

# 1. Test basic network connectivity
echo "1️⃣ Testing network connectivity (ping)..."
if ping -c 2 -W 2 $GCP_IP >/dev/null 2>&1; then
    echo "   ✅ Server is reachable via ping"
else
    echo "   ❌ Server not responding to ping"
fi
echo ""

# 2. Test port connectivity
echo "2️⃣ Testing port $PORT connectivity..."
timeout 5 bash -c "cat < /dev/null > /dev/tcp/$GCP_IP/$PORT" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Port $PORT is open"
else
    echo "   ❌ Port $PORT is closed or filtered"
    echo "   💡 Possible issues:"
    echo "      - LlamaCPP service is not running"
    echo "      - GCP firewall blocking port $PORT"
    echo "      - Service listening on localhost only (not 0.0.0.0)"
fi
echo ""

# 3. Try HTTP endpoints
echo "3️⃣ Testing HTTP endpoints (10s timeout)..."
ENDPOINTS=(
    "/"
    "/health"
    "/v1/models"
    "/models"
    "/completion"
)

for endpoint in "${ENDPOINTS[@]}"; do
    printf "   Testing %-25s" "$endpoint"
    response=$(curl -s -m 10 -o /dev/null -w "%{http_code}" "http://$GCP_IP:$PORT$endpoint" 2>/dev/null)
    if [ "$response" = "000" ]; then
        echo "❌ TIMEOUT/NO_RESPONSE"
    elif [ "$response" = "200" ]; then
        echo "✅ $response OK"
    else
        echo "⚠️  $response"
    fi
done
echo ""

# 4. Compare with working Ollama GCP
echo "4️⃣ Comparing with working Ollama GCP (34.60.255.199:11434)..."
OLLAMA_RESPONSE=$(curl -s -m 5 -o /dev/null -w "%{http_code}" "http://34.60.255.199:11434/" 2>/dev/null)
if [ "$OLLAMA_RESPONSE" = "200" ]; then
    echo "   ✅ Ollama GCP is responding ($OLLAMA_RESPONSE)"
    echo "   💡 This confirms network connectivity to GCP is working"
else
    echo "   ⚠️  Ollama GCP response: $OLLAMA_RESPONSE"
fi
echo ""

# 5. Next steps
echo "======================================"
echo "🔧 Recommended Actions:"
echo ""
echo "If port is CLOSED/FILTERED:"
echo "  1. SSH to GCP instance:"
echo "     gcloud compute ssh llama-cpp-server --zone=<zone>"
echo ""
echo "  2. Check if LlamaCPP is running:"
echo "     ps aux | grep llama"
echo "     sudo systemctl status llama-cpp"
echo ""
echo "  3. Check what's listening on port 8000:"
echo "     sudo netstat -tlnp | grep 8000"
echo "     sudo lsof -i :8000"
echo ""
echo "  4. Check GCP firewall rules:"
echo "     gcloud compute firewall-rules list | grep llama"
echo ""
echo "  5. If service not running, start it:"
echo "     sudo systemctl start llama-cpp"
echo "     # OR manually:"
echo "     ./llama-cpp-server --host 0.0.0.0 --port 8000 --model <model-path>"
echo ""
echo "  6. Create firewall rule if needed:"
echo "     gcloud compute firewall-rules create allow-llama-cpp \\"
echo "       --allow tcp:8000 \\"
echo "       --source-ranges 0.0.0.0/0 \\"
echo "       --target-tags llama-cpp-server"
echo ""
echo "If ping fails but Ollama works:"
echo "  - ICMP may be blocked (normal)"
echo "  - Focus on fixing the LlamaCPP service/port issue"
echo ""
