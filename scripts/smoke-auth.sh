#!/usr/bin/env bash
# scripts/smoke-auth.sh
#
# 5-step manual smoke test for the auth flow:
#   register -> login -> refresh -> logout -> login
#
# Prerequisites:
#   - Backend running: make api-dev (or make api-docker-up)
#   - curl and python3 available
#
# Usage:
#   bash scripts/smoke-auth.sh [BASE_URL]
#   bash scripts/smoke-auth.sh http://127.0.0.1:8001

set -euo pipefail

BASE="${1:-http://127.0.0.1:8001}"
API="${BASE}/api/v1"
EMAIL="smoke-test-$(date +%s)@example.com"
PASSWORD="SmokeTest!234"
NAME="Smoke Test User"

PASS=0
FAIL=0

step() { echo ""; echo "=== Step $1: $2 ==="; }
ok()   { echo "  PASS: $1"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

# Helper: extract a JSON field value using python3
json_field() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)" 2>/dev/null || echo ""
}

echo "Auth smoke test against ${API}"
echo "  Email: ${EMAIL}"

# ─── Step 0: Get CSRF token ──────────────────────────────────────────────────
step 0 "Get CSRF token"
CSRF_RESPONSE=$(curl -s -w "\n%{http_code}" "${API}/auth/csrf-token")
CSRF_BODY=$(echo "$CSRF_RESPONSE" | head -n -1)
CSRF_CODE=$(echo "$CSRF_RESPONSE" | tail -1)
CSRF_TOKEN=$(echo "$CSRF_BODY" | json_field "['csrf_token']")

if [ -n "$CSRF_TOKEN" ] && [ "$CSRF_CODE" = "200" ]; then
  ok "CSRF token obtained (${CSRF_TOKEN:0:16}...)"
else
  fail "CSRF token request failed (HTTP ${CSRF_CODE})"
  echo "  Response: ${CSRF_BODY}"
  exit 1
fi

# ─── Step 1: Register ────────────────────────────────────────────────────────
step 1 "Register (${EMAIL})"
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"name\":\"${NAME}\",\"csrf_token\":\"${CSRF_TOKEN}\"}")
REGISTER_BODY=$(echo "$REGISTER_RESPONSE" | head -n -1)
REGISTER_CODE=$(echo "$REGISTER_RESPONSE" | tail -1)

ACCESS_TOKEN=$(echo "$REGISTER_BODY" | json_field "['data']['access_token']")
REFRESH_TOKEN=$(echo "$REGISTER_BODY" | json_field "['data']['refresh_token']")
USER_ID=$(echo "$REGISTER_BODY" | json_field "['data']['user']['id']")

if [ "$REGISTER_CODE" = "200" ] && [ -n "$ACCESS_TOKEN" ]; then
  ok "Registered user ${USER_ID}"
  ok "Got access_token (${ACCESS_TOKEN:0:20}...)"
  ok "Got refresh_token (${REFRESH_TOKEN:0:20}...)"
else
  fail "Register failed (HTTP ${REGISTER_CODE})"
  echo "  Response: ${REGISTER_BODY}"
  exit 1
fi

# ─── Step 2: Login ───────────────────────────────────────────────────────────
step 2 "Login (${EMAIL})"
LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"csrf_token\":\"${CSRF_TOKEN}\"}")
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | head -n -1)
LOGIN_CODE=$(echo "$LOGIN_RESPONSE" | tail -1)

LOGIN_ACCESS=$(echo "$LOGIN_BODY" | json_field "['data']['access_token']")
LOGIN_REFRESH=$(echo "$LOGIN_BODY" | json_field "['data']['refresh_token']")

if [ "$LOGIN_CODE" = "200" ] && [ -n "$LOGIN_ACCESS" ]; then
  ok "Login successful, got new tokens"
  ACCESS_TOKEN="$LOGIN_ACCESS"
  REFRESH_TOKEN="$LOGIN_REFRESH"
else
  fail "Login failed (HTTP ${LOGIN_CODE})"
  echo "  Response: ${LOGIN_BODY}"
fi

# ─── Step 3: Refresh token ───────────────────────────────────────────────────
step 3 "Refresh access token"
REFRESH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"${REFRESH_TOKEN}\"}")
REFRESH_BODY=$(echo "$REFRESH_RESPONSE" | head -n -1)
REFRESH_CODE=$(echo "$REFRESH_RESPONSE" | tail -1)

NEW_ACCESS=$(echo "$REFRESH_BODY" | json_field "['data']['access_token']")
NEW_REFRESH=$(echo "$REFRESH_BODY" | json_field "['data']['refresh_token']")

if [ "$REFRESH_CODE" = "200" ] && [ -n "$NEW_ACCESS" ]; then
  ok "Token refreshed successfully"
  ACCESS_TOKEN="$NEW_ACCESS"
  REFRESH_TOKEN="$NEW_REFRESH"
else
  fail "Refresh failed (HTTP ${REFRESH_CODE})"
  echo "  Response: ${REFRESH_BODY}"
fi

# ─── Step 4: Logout ──────────────────────────────────────────────────────────
step 4 "Logout"
LOGOUT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API}/auth/logout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")
LOGOUT_BODY=$(echo "$LOGOUT_RESPONSE" | head -n -1)
LOGOUT_CODE=$(echo "$LOGOUT_RESPONSE" | tail -1)

LOGOUT_MSG=$(echo "$LOGOUT_BODY" | json_field "['data']['message']")

if [ "$LOGOUT_CODE" = "200" ]; then
  ok "Logged out: ${LOGOUT_MSG}"
else
  fail "Logout failed (HTTP ${LOGOUT_CODE})"
  echo "  Response: ${LOGOUT_BODY}"
fi

# ─── Step 5: Login again ─────────────────────────────────────────────────────
step 5 "Login again (${EMAIL})"
LOGIN2_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"csrf_token\":\"${CSRF_TOKEN}\"}")
LOGIN2_BODY=$(echo "$LOGIN2_RESPONSE" | head -n -1)
LOGIN2_CODE=$(echo "$LOGIN2_RESPONSE" | tail -1)

LOGIN2_ACCESS=$(echo "$LOGIN2_BODY" | json_field "['data']['access_token']")

if [ "$LOGIN2_CODE" = "200" ] && [ -n "$LOGIN2_ACCESS" ]; then
  ok "Re-login successful, got new tokens"
else
  fail "Re-login failed (HTTP ${LOGIN2_CODE})"
  echo "  Response: ${LOGIN2_BODY}"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "======================================="
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "======================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "All auth smoke tests passed."