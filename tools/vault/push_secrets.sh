#!/usr/bin/env bash
# Usage: ./tools/vault/push_secrets.sh <env-file> <vault-path>
# Push environment variables from a .env file to HashiCorp Vault
set -euo pipefail

ENV_FILE=${1:-.env}
VAULT_PATH=${2:-secret/goblin-assistant}

if [[ -z "${VAULT_ADDR:-}" || -z "${VAULT_TOKEN:-}" ]]; then
  echo "ERROR: VAULT_ADDR and VAULT_TOKEN must be set."
  echo "Example: export VAULT_ADDR='https://vault.example.com:8200'"
  echo "         export VAULT_TOKEN='s.xxxxxx'"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE"
  exit 1
fi

# Check if vault CLI is available
if ! command -v vault >/dev/null 2>&1; then
  echo "ERROR: vault CLI is not installed. Install with: brew install vault"
  exit 1
fi

declare -a payload=()
while IFS='=' read -r key value || [ -n "$key" ]; do
  # Skip empty lines and comments
  [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
  # Remove whitespace from key
  key="$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  # Remove carriage return from value
  value="${value%$'\r'}"
  # Skip if key is empty after trimming
  [[ -z "$key" ]] && continue
  payload+=("${key}=${value}")
done < "$ENV_FILE"

if [[ ${#payload[@]} -eq 0 ]]; then
  echo "ERROR: No valid key-value pairs found in $ENV_FILE"
  exit 1
fi

echo "Putting ${#payload[@]} key(s) into Vault path ${VAULT_PATH}"
echo "Note: Values are not echoed for security"

vault kv put "$VAULT_PATH" "${payload[@]}"

echo "✅ Successfully pushed secrets to Vault path: $VAULT_PATH"
echo "⚠️  WARNING: Ensure $ENV_FILE is not committed to version control"
