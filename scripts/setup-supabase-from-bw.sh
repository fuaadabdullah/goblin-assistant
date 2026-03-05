#!/usr/bin/env bash
set -euo pipefail

# apps/goblin-assistant/scripts/setup-supabase-from-bw.sh
# Fetch Supabase credentials from Bitwarden and validate using Supabase CLI + local check script

cd "$(dirname "$0")/.."

echo "🔎 Ensuring Bitwarden CLI and Supabase CLI are installed..."
if ! command -v bw &> /dev/null; then
  echo "❌ Bitwarden CLI not found. Installing @bitwarden/cli (global npm)..."
  npm install -g @bitwarden/cli
fi

if ! command -v supabase &> /dev/null; then
  echo "❌ Supabase CLI not found. Installing supabase (global npm)..."
  npm install -g supabase
fi

echo "🔐 Unlocking Bitwarden vault (you may be prompted)..."
export BW_SESSION=$(bw unlock --raw)

# Helper to try multiple secret item names
bw_get() {
  local names=("$@")
  local val
  for n in "${names[@]}"; do
    if val=$(bw get password "$n" 2>/dev/null); then
      echo "$val"
      return 0
    fi
  done
  return 1
}

echo "📦 Fetching Supabase secrets from Bitwarden..."
SUPABASE_URL=$(bw_get goblin-prod-supabase-url supabase-url goblin-assistant-supabase-url goblin-supabase-url || true)
SUPABASE_ANON_KEY=$(bw_get goblin-prod-supabase-anon-key supabase-anon-key goblin-assistant-supabase-anon-key goblin-supabase-anon-key || true)
SUPABASE_SERVICE_ROLE_KEY=$(bw_get goblin-prod-supabase-service-role-key supabase-service-role-key goblin-assistant-supabase-service-role-key goblin-supabase-service-role-key || true)
SUPABASE_ACCESS_TOKEN=$(bw_get goblin-supabase-access-token supabase-access-token goblin-assistant-supabase-access-token || true)

echo "→ Supabase URL: ${SUPABASE_URL:-'(not found)'}"
echo "→ Supabase ANON Key: ${SUPABASE_ANON_KEY:+'present (hidden)'}"
echo "→ Supabase SERVICE Role Key: ${SUPABASE_SERVICE_ROLE_KEY:+'present (hidden)'}"
echo "→ Supabase CLI Access Token: ${SUPABASE_ACCESS_TOKEN:+'present (hidden)'}"

if [ -z "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  echo "⚠️  SERVICE Role Key is missing from Bitwarden — add 'goblin-prod-supabase-service-role-key' or 'supabase-service-role-key' to your vault if you need admin/database write operations."
fi

if [ -z "${SUPABASE_ACCESS_TOKEN:-}" ]; then
  echo "⚠️  Supabase CLI Access Token is missing — add 'goblin-supabase-access-token' or 'supabase-access-token' if you want to use supabase CLI commands for project management."
fi

if [ -z "${SUPABASE_URL:-}" ] || [ -z "${SUPABASE_ANON_KEY:-}" ]; then
  echo "\nMissing SUPABASE_URL or SUPABASE_ANON_KEY from Bitwarden. Please add them to your vault or set env vars manually."
  exit 1
fi

export SUPABASE_URL
export SUPABASE_ANON_KEY
export SUPABASE_SERVICE_ROLE_KEY
export SUPABASE_ACCESS_TOKEN

echo "✅ Env vars exported for current shell session. Now validating connectivity..."

if [ -n "${SUPABASE_ACCESS_TOKEN:-}" ]; then
  echo "Attempting Supabase CLI validation (projects list) using SUPABASE_ACCESS_TOKEN..."
  # supabase CLI reads SUPABASE_ACCESS_TOKEN env var; projects list will validate token
  if supabase projects list >/dev/null 2>&1; then
    echo "✅ Supabase CLI authenticated and able to list projects."
  else
    echo "⚠️  Supabase CLI failed to list projects with provided access token (may be insufficient scope)."
  fi
else
  echo "No SUPABASE_ACCESS_TOKEN available; skipping supabase CLI project validation."
fi

echo "Running local JS-based connectivity check script..."
if npx tsx scripts/check-supabase.ts; then
  echo "✅ Local Supabase connectivity check passed."
else
  echo "❌ Local Supabase connectivity check failed. Check keys and network access."
fi

echo "📝 Updating .env.local with fetched credentials..."
# Update or add NEXT_PUBLIC_SUPABASE_URL
if grep -q "^NEXT_PUBLIC_SUPABASE_URL=" .env.local; then
  sed -i.bak "s|^NEXT_PUBLIC_SUPABASE_URL=.*|NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL|" .env.local
else
  echo "NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL" >> .env.local
fi

# Update or add NEXT_PUBLIC_SUPABASE_ANON_KEY
if grep -q "^NEXT_PUBLIC_SUPABASE_ANON_KEY=" .env.local; then
  sed -i.bak "s|^NEXT_PUBLIC_SUPABASE_ANON_KEY=.*|NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY|" .env.local
else
  echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" >> .env.local
fi

# Update or add SUPABASE_SERVICE_ROLE_KEY (only if we have it)
if [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  if grep -q "^SUPABASE_SERVICE_ROLE_KEY=" .env.local; then
    sed -i.bak "s|^SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY|" .env.local
  else
    echo "SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY" >> .env.local
  fi
fi

echo "✅ .env.local updated with Supabase credentials from Bitwarden."

echo "Cleaning up BW session from environment..."
unset BW_SESSION || true

echo "Done."
