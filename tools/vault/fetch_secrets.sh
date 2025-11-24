#!/usr/bin/env bash
# Usage: ./tools/vault/fetch_secrets.sh <vault-path> [output-file]
# Fetch secrets from HashiCorp Vault and save to a local file or export to environment
set -euo pipefail

VAULT_PATH=${1:-secret/goblin-assistant}
OUT_FILE=${2:-.env.vault}

if [[ -z "${VAULT_ADDR:-}" || -z "${VAULT_TOKEN:-}" ]]; then
  echo "ERROR: VAULT_ADDR and VAULT_TOKEN must be set."
  echo "Example: export VAULT_ADDR='https://vault.example.com:8200'"
  echo "         export VAULT_TOKEN='s.xxxxxx'"
  exit 1
fi

# Check if vault CLI is available
if ! command -v vault >/dev/null 2>&1; then
  echo "ERROR: vault CLI is not installed. Install with: brew install vault"
  exit 1
fi

# Check if jq is available
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is not installed. Install with: brew install jq"
  exit 1
fi

echo "Fetching secrets from Vault path: $VAULT_PATH"

# Fetch secrets and format as KEY=VALUE pairs
vault kv get -format=json "$VAULT_PATH" | \
  jq -r '.data.data | to_entries | .[] | "\(.key)=\(.value)"' > "$OUT_FILE"

if [[ ! -s "$OUT_FILE" ]]; then
  echo "ERROR: No secrets found or failed to fetch from Vault"
  exit 1
fi

echo "✅ Successfully saved ${OUT_FILE} secrets to: $OUT_FILE"
echo "⚠️  WARNING: This file contains sensitive data - do not commit to version control"
echo ""
echo "To load secrets into environment:"
echo "  export \$(cat $OUT_FILE | xargs)"
echo ""
echo "To verify secrets were loaded:"
echo "  env | grep -E '(API_KEY|TOKEN)' | head -5"
