#!/usr/bin/env bash
# scripts/smoke-chat.sh
#
# End-to-end chat smoke test: proxy -> backend -> LLM -> response.
#
# Sends one message through the chat endpoint and verifies the response.
# Requires a valid provider API key (e.g., OPENAI_API_KEY) in .env.
#
# Prerequisites:
#   - Backend running: make api-dev (or make api-docker-up)
#   - Provider key set: OPENAI_API_KEY (or another active provider)
#   - curl and python3 available
#
# Usage:
#   bash scripts/smoke-chat.sh [BASE_URL] [PROVIDER]
#   bash scripts/smoke-chat.sh http://127.0.0.1:8001 openai

set -euo pipefail

BASE="${1:-http://127.0.0.1:8001}"
PROVIDER="${2:-openai}"
API="${BASE}/api/v1"

echo "Chat E2E smoke test"
echo "  Backend:  ${API}"
echo "  Provider: ${PROVIDER}"
echo ""

# ─── Step 1: Check backend health ────────────────────────────────────────────
echo "=== Step 1: Backend health check ==="
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${API}/health" 2>/dev/null || echo -e "\n000")
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)

if [ "$HEALTH_CODE" = "200" ]; then
  echo "  PASS: Backend is healthy"
else
  echo "  FAIL: Backend health check failed (HTTP ${HEALTH_CODE})"
  echo "  Response: ${HEALTH_BODY}"
  echo ""
  echo "  Start the backend first: make api-dev"
  exit 1
fi

# ─── Step 2: Send a chat message ─────────────────────────────────────────────
echo ""
echo "=== Step 2: Send chat message ==="
echo "  Message: 'Say hello in exactly 3 words.'"

CHAT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API}/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [{\"role\": \"user\", \"content\": \"Say hello in exactly 3 words.\"}],
    \"provider\": \"${PROVIDER}\"
  }" \
  --max-time 60 2>/dev/null || echo -e "\n000")

CHAT_BODY=$(echo "$CHAT_RESPONSE" | head -n -1)
CHAT_CODE=$(echo "$CHAT_RESPONSE" | tail -1)

if [ "$CHAT_CODE" = "200" ]; then
  # Extract the response text
  RESPONSE_TEXT=$(python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # Handle SuccessEnvelope format: {ok: true, data: {result: {text: ...}}}
    if 'data' in d and 'result' in d['data']:
        print(d['data']['result'].get('text', ''))
    elif 'result' in d:
        print(d['result'].get('text', ''))
    elif 'content' in d:
        print(d['content'])
    else:
        print(str(d))
except Exception as e:
    print(f'(parse error: {e})')
" <<< "$CHAT_BODY" 2>/dev/null || echo "(failed to parse)")

  PROVIDER_USED=$(python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'data' in d:
        print(d['data'].get('provider', 'unknown'))
    else:
        print(d.get('provider', 'unknown'))
except:
    print('unknown')
" <<< "$CHAT_BODY" 2>/dev/null || echo "unknown")

  echo "  PASS: Chat response received"
  echo "  Provider used: ${PROVIDER_USED}"
  echo "  Response: ${RESPONSE_TEXT}"

  # Check if we got a mock response
  if [ "$PROVIDER_USED" = "mock" ]; then
    echo ""
    echo "  WARNING: Got mock provider response."
    echo "  This means no real provider key is configured."
    echo "  Set OPENAI_API_KEY (or another provider key) in .env and restart."
  fi
else
  echo "  FAIL: Chat request failed (HTTP ${CHAT_CODE})"
  echo "  Response: ${CHAT_BODY}"
  echo ""

  # Provide troubleshooting hints
  case "$CHAT_CODE" in
    503)
      echo "  Hint: 503 means the backend is running but no provider is configured."
      echo "  Set OPENAI_API_KEY in .env and restart the backend."
      ;;
    401|403)
      echo "  Hint: Auth error. Check that SECRET_KEY is set in .env."
      ;;
    000)
      echo "  Hint: Connection refused. Is the backend running?"
      echo "  Start it with: make api-dev"
      ;;
  esac
  exit 1
fi

# ─── Step 3: Verify via frontend proxy (if running) ─────────────────────────
echo ""
echo "=== Step 3: Frontend proxy check (optional) ==="
PROXY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:3000/api/generate" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Say hello in exactly 3 words.\"}" \
  --max-time 30 2>/dev/null || echo -e "\n000")

PROXY_CODE=$(echo "$PROXY_RESPONSE" | tail -1)

if [ "$PROXY_CODE" = "200" ]; then
  PROXY_BODY=$(echo "$PROXY_RESPONSE" | head -n -1)
  echo "  PASS: Frontend proxy is working"
  echo "  Response: ${PROXY_BODY:0:200}"
elif [ "$PROXY_CODE" = "000" ]; then
  echo "  SKIP: Frontend not running on :3000 (start with: make web-dev)"
else
  echo "  FAIL: Frontend proxy returned HTTP ${PROXY_CODE}"
fi

echo ""
echo "======================================="
echo "  Chat E2E smoke test complete"
echo "======================================="