#!/usr/bin/env bash
# scripts/bootstrap-env.sh
#
# One-shot interactive bootstrap for provider API keys and core secrets.
#
# Prompts for each key once, writes them to .env at the repo root, and
# optionally pulls values from Bitwarden (wiring setup_bitwarden.sh and
# setup-supabase-from-bw.sh).
#
# Usage:
#   bash scripts/bootstrap-env.sh              # interactive
#   bash scripts/bootstrap-env.sh --bw         # Bitwarden mode (pull from vault)
#   bash scripts/bootstrap-env.sh --check      # audit only, don't write

set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env"
BW_MODE=false
CHECK_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --bw)    BW_MODE=true ;;
    --check) CHECK_ONLY=true ;;
  esac
done

# ─── Helpers ─────────────────────────────────────────────────────────────────

# All provider keys the backend expects (sourced from config/providers.toml).
# Format: "ENV_VAR_NAME|Bitwarden item name|human label|required for dogfooding"
declare -a SECRETS=(
  "OPENAI_API_KEY|goblin-dev-openai-key|OpenAI API key|required"
  "ANTHROPIC_API_KEY|goblin-dev-anthropic-key|Anthropic API key|optional"
  "GROQ_API_KEY|goblin-dev-groq-key|Groq API key|optional"
  "SILICONEFLOW_API_KEY|goblin-dev-siliconeflow-key|SiliconeFlow API key|optional"
  "GOOGLE_AI_API_KEY|goblin-dev-google-ai-key|Google AI / Gemini API key|optional"
  "DEEPSEEK_API_KEY|goblin-dev-deepseek-key|DeepSeek API key|optional"
  "TOGETHER_API_KEY|goblin-dev-together-key|Together AI API key|optional"
  "HUGGINGFACE_API_KEY|goblin-dev-huggingface-key|Hugging Face API key|optional"
  "COHERE_API_KEY|goblin-dev-cohere-key|Cohere API key|optional"
  "DASHSCOPE_API_KEY|goblin-dev-dashscope-key|Aliyun DashScope API key|optional"
  "AZURE_API_KEY|goblin-dev-azure-key|Azure OpenAI API key|optional"
  "ATLASSIAN_API_TOKEN|goblin-dev-atlassian-token|Atlassian / Rovo Dev token|optional"
)

# Core infrastructure secrets (non-provider).
declare -a INFRA_SECRETS=(
  "SECRET_KEY|goblin-dev-fastapi-secret|FastAPI / JWT signing secret|required"
  "SUPABASE_URL|goblin-prod-supabase-url|Supabase project URL|required"
  "SUPABASE_ANON_KEY|goblin-prod-supabase-anon-key|Supabase anon key|required"
  "SUPABASE_SERVICE_ROLE_KEY|goblin-prod-supabase-service-role-key|Supabase service role key|optional"
  "SENTRY_DSN|goblin-dev-sentry-dsn|Sentry DSN|optional"
)

# GCP LLM endpoints — VMs terminated 2026-01-11.  These are kept as
# placeholders so the config doesn't break, but they should be empty.
declare -a GCP_STALE=(
  "OLLAMA_GCP_ENDPOINT||Ollama GCP endpoint (VM terminated)|stale"
  "LLAMACPP_GCP_ENDPOINT||LlamaCPP GCP endpoint (VM terminated)|stale"
  "GOOGLE_CLOUD_VLLM_ENDPOINT||GCP vLLM endpoint (VM terminated)|stale"
  "GOOGLE_CLOUD_VLLM_API_KEY||GCP vLLM API key (VM terminated)|stale"
)

bw_get() {
  # Try multiple item name variants from the Bitwarden vault.
  local names=("$@")
  local val
  for n in "${names[@]}"; do
    if [ -n "$n" ] && val=$(bw get password "$n" 2>/dev/null) && [ -n "$val" ]; then
      echo "$val"
      return 0
    fi
  done
  return 1
}

set_env_var() {
  local key="$1" val="$2"
  if [ "$CHECK_ONLY" = true ]; then return; fi
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

prompt_secret() {
  local env_var="$1" bw_name="$2" label="$3" priority="$4"
  local val=""

  if [ "$BW_MODE" = true ]; then
    # Try Bitwarden first.
    if val=$(bw_get "$bw_name" "${bw_name/goblin-dev-/goblin-prod-}" 2>/dev/null); then
      echo "  [ok] ${label}: pulled from Bitwarden (${bw_name})"
      set_env_var "$env_var" "$val"
      return
    else
      echo "  [warn] ${label}: not found in Bitwarden vault (${bw_name})"
    fi
  fi

  # Interactive prompt (skip in --check mode).
  if [ "$CHECK_ONLY" = true ]; then
    # In check mode, just report whether the var is already set.
    if grep -q "^${env_var}=.\+" "$ENV_FILE" 2>/dev/null; then
      echo "  [ok] ${label}: already set in .env"
    else
      echo "  [MISSING] ${label}: MISSING from .env [${priority}]"
    fi
    return
  fi

  if [ "$priority" = "stale" ]; then
    echo "  [skip] ${label}: skipping (stale - GCP VMs terminated 2026-01-11)"
    set_env_var "$env_var" ""
    return
  fi

  read -s -p "  Enter ${label} [${priority}, press Enter to skip]: " val
  echo
  if [ -n "$val" ]; then
    set_env_var "$env_var" "$val"
    echo "  [ok] ${label}: saved"
  else
    echo "  [skip] ${label}: skipped"
  fi
}

# ─── Main ────────────────────────────────────────────────────────────────────

echo "=============================================================="
echo "  Goblin Assistant - Provider Key & Secret Bootstrap"
echo "=============================================================="
echo ""

# Ensure .env exists.
if [ ! -f "$ENV_FILE" ] && [ "$CHECK_ONLY" = false ]; then
  echo "Creating ${ENV_FILE} from .env.example..."
  cp .env.example "$ENV_FILE"
  echo ""
fi

# ─── Bitwarden Setup ─────────────────────────────────────────────────────────

if [ "$BW_MODE" = true ]; then
  echo "Bitwarden Mode - pulling secrets from vault"
  echo "  (Run scripts/setup_bitwarden.sh first if vault items don't exist)"
  echo ""

  # Ensure BW CLI is installed.
  if ! command -v bw &> /dev/null; then
    echo "Installing Bitwarden CLI..."
    npm install -g @bitwarden/cli
  fi

  # Unlock vault.
  if [ -z "${BW_SESSION:-}" ]; then
    echo "Unlocking Bitwarden vault..."
    export BW_SESSION=$(bw unlock --raw)
  fi
  echo "Bitwarden session active"
  echo ""

  # Run Supabase setup script (fetches + validates Supabase creds).
  echo "Fetching Supabase credentials from Bitwarden..."
  if bash scripts/setup-supabase-from-bw.sh; then
    echo "Supabase credentials loaded"
  else
    echo "WARNING: Supabase setup failed - you'll need to set SUPABASE_* vars manually"
  fi
  echo ""
fi

# ─── Provider Keys ───────────────────────────────────────────────────────────

echo "--- Provider API Keys ---"
echo "    Dogfooding provider: OpenAI (OPENAI_API_KEY is required)"
echo "    GCP LLM endpoints were removed (VMs terminated 2026-01-11)"
echo ""

for entry in "${SECRETS[@]}"; do
  IFS='|' read -r env_var bw_name label priority <<< "$entry"
  prompt_secret "$env_var" "$bw_name" "$label" "$priority"
done

echo ""

# ─── Infrastructure Secrets ──────────────────────────────────────────────────

echo "--- Infrastructure Secrets ---"
for entry in "${INFRA_SECRETS[@]}"; do
  IFS='|' read -r env_var bw_name label priority <<< "$entry"
  prompt_secret "$env_var" "$bw_name" "$label" "$priority"
done

echo ""

# ─── Stale GCP Endpoints ─────────────────────────────────────────────────────

echo "--- Stale GCP Endpoints (VMs terminated 2026-01-11) ---"
for entry in "${GCP_STALE[@]}"; do
  IFS='|' read -r env_var bw_name label priority <<< "$entry"
  prompt_secret "$env_var" "$bw_name" "$label" "$priority"
done

echo ""

# ─── Summary ─────────────────────────────────────────────────────────────────

if [ "$CHECK_ONLY" = true ]; then
  echo "=== Audit Summary ==="
  echo "Check .env for any [MISSING] marks above."
else
  echo "=== Bootstrap Complete ==="
  echo ""
  echo "Written to: ${ENV_FILE}"
  echo ""
  echo "Next steps:"
  echo "  1. Review ${ENV_FILE} and fill any skipped values"
  echo "  2. For dogfooding, ensure OPENAI_API_KEY is set"
  echo "  3. Start the stack: make api-dev && make web-dev"
  echo "  4. Verify: curl http://127.0.0.1:8001/api/v1/health"
  echo ""
  echo "Reminder: never commit .env - it's in .gitignore"
fi

# Clean up BW session if we started it.
if [ "$BW_MODE" = true ] && [ -n "${BW_SESSION:-}" ]; then
  unset BW_SESSION || true
fi