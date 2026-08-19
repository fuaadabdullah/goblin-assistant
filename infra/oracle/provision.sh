#!/usr/bin/env bash
# Provision the Oracle Cloud ARM instance, retrying until capacity is available.
#
# Oracle's free ARM tier frequently returns "Out of host capacity" — this is
# normal and the only fix is to keep retrying. This script does that automatically.
#
# Usage:
#   cd infra/oracle/terraform
#   cp terraform.tfvars.example terraform.tfvars   # fill in your OCI credentials
#   cd ..
#   ./provision.sh
#
# Optional env vars:
#   RETRY_INTERVAL_SECONDS  — seconds between attempts (default: 300 = 5 min)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/terraform"
INTERVAL="${RETRY_INTERVAL_SECONDS:-300}"

if [ ! -f "$TF_DIR/terraform.tfvars" ]; then
  echo "Error: $TF_DIR/terraform.tfvars not found."
  echo "  cp $TF_DIR/terraform.tfvars.example $TF_DIR/terraform.tfvars"
  echo "  # fill in your OCI credentials, then re-run"
  exit 1
fi

cd "$TF_DIR"
terraform init -upgrade -input=false

echo ""
echo "Provisioning Oracle Cloud ARM instance (VM.Standard.A1.Flex, 4 OCPU / 24 GB)"
echo "Retrying every ${INTERVAL}s if capacity is unavailable. Ctrl+C to stop."
echo ""

ATTEMPT=0
while true; do
  ATTEMPT=$((ATTEMPT + 1))
  TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

  echo "[$TIMESTAMP] Attempt $ATTEMPT — terraform apply"

  # Capture output so we can inspect the error before deciding to retry
  TF_OUTPUT="$(mktemp)"
  if terraform apply -auto-approve -input=false 2>&1 | tee "$TF_OUTPUT"; then
    rm -f "$TF_OUTPUT"
    echo ""
    echo "Instance provisioned on attempt $ATTEMPT."
    echo ""
    terraform output
    exit 0
  fi

  # Only retry on the specific OCI capacity error; fail fast on anything else
  if grep -qi "out of host capacity" "$TF_OUTPUT"; then
    rm -f "$TF_OUTPUT"
    echo "[$TIMESTAMP] Capacity unavailable. Waiting ${INTERVAL}s before retry..."
    sleep "$INTERVAL"
  else
    rm -f "$TF_OUTPUT"
    echo ""
    echo "Unrecoverable error (not a capacity issue). Fix the config above and re-run."
    exit 1
  fi
done
