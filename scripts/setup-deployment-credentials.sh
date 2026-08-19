#!/usr/bin/env bash
set -euo pipefail

# Legacy compatibility helper for deployment credential setup.
#
# This repository no longer requires a Terraform variables file in the current
# checkout. If a terraform/ directory exists, this script can still populate
# terraform/terraform.tfvars. Otherwise it prints the preferred hybrid setup
# path and exits successfully.
#
# Usage: ./scripts/setup-deployment-credentials.sh

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TERRAFORM_VARS="$ROOT_DIR/terraform/terraform.tfvars"
EXAMPLE_VARS="$ROOT_DIR/terraform/terraform.tfvars.example"

echo "Starting deployment credentials setup..."

if [ ! -d "$ROOT_DIR/terraform" ]; then
  echo "Terraform directory not present in this checkout."
  echo "Use the hybrid CI/CD setup instead:"
  echo "  ./scripts/setup-ci-cd.sh"
  echo "  ./scripts/setup-github-secrets.sh <owner> <repo>"
  echo "  ./scripts/setup-circleci.sh gh <org> <repo>"
  echo "If you are working in a Terraform-enabled checkout, run this helper there."
  exit 0
fi

if [ ! -f "$TERRAFORM_VARS" ]; then
  if [ -f "$EXAMPLE_VARS" ]; then
    echo "Creating $TERRAFORM_VARS from example"
    cp "$EXAMPLE_VARS" "$TERRAFORM_VARS"
  else
    echo "Error: example file not found at $EXAMPLE_VARS"
    exit 1
  fi
fi

prompt() {
  local var_name=$1
  local prompt_msg=$2
  local hide=${3:-false}

  if [ "$hide" = true ]; then
    read -rs -p "$prompt_msg: " val
    echo
  else
    read -p "$prompt_msg: " val
  fi

  if [ -n "$val" ]; then
    # Escape slashes for sed
    esc=$(printf '%s' "$val" | sed -e 's/[\/&]/\\&/g')
    sed -i.bak -E "s|(^\s*${var_name}\s*=\s*).*$|\1\"${esc}\"|" "$TERRAFORM_VARS" || true
    rm -f "$TERRAFORM_VARS.bak"
    echo "Updated $var_name"
  else
    echo "Skipped $var_name"
  fi
}

echo "-- You can press Enter to skip any value and fill it later --"

prompt "render_api_key" "Render API key (starts with rnd_)"
prompt "github_token" "GitHub personal access token (ghp_... or github_pat_...)" true
prompt "database_url" "Postgres DATABASE_URL (postgresql://...)"

read -p "JWT secret (leave empty to auto-generate): " JWT
if [ -z "$JWT" ]; then
  JWT=$(openssl rand -hex 32)
  echo "Generated JWT secret"
fi
prompt_value="${JWT}"
esc=$(printf '%s' "$prompt_value" | sed -e 's/[\/&]/\\&/g')
sed -i.bak -E "s|(^\s*jwt_secret_key\s*=\s*).*$|\1\"${esc}\"|" "$TERRAFORM_VARS" || true
rm -f "$TERRAFORM_VARS.bak"
echo "Updated jwt_secret_key"

prompt "supabase_url" "Supabase project URL"
prompt "supabase_service_role_key" "Supabase service_role key" true
prompt "supabase_anon_key" "Supabase anon key" true

echo "All done. Review $TERRAFORM_VARS and then commit the file to your branch."
echo "Recommended: git add $TERRAFORM_VARS && git commit -m 'config: add deployment credentials'"

exit 0
