#!/usr/bin/env bash
# pip-audit.sh — Run pip-audit against the locked uv environment for goblin-assistant-api.
#
# Usage:
#   ./scripts/security/pip-audit.sh              # human-readable output
#   ./scripts/security/pip-audit.sh --json        # JSON output (consumed by CI)
#
# Exits 0 if no fixable vulns found, 1 otherwise.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$REPO_ROOT/apps/api"
REPORT_DIR="$REPO_ROOT/reports"
REPORT_FILE="$REPORT_DIR/pip-audit-latest.json"

mkdir -p "$REPORT_DIR"

# Ensure the locked uv environment is synced (dev extras needed for pip-audit itself).
echo "==> Syncing locked environment (uv sync --frozen)..."
cd "$API_DIR"
uv sync --frozen --extra dev --quiet

# Run pip-audit against the *locked* environment, not the ambient one.
#   --desc            — include vulnerability descriptions
#   --progress-spinner off — cleaner CI output
AUDIT_ARGS=(
    --desc
    --progress-spinner off
)

# If --json flag is passed, produce JSON output for CI consumption.
if [[ "${1:-}" == "--json" ]]; then
    AUDIT_ARGS+=(--format json)
    echo "==> Running pip-audit (JSON mode) → $REPORT_FILE"
else
    echo "==> Running pip-audit (human-readable)..."
fi

# pip-audit runs inside the uv-managed .venv
VENV_PYTHON="$API_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "ERROR: venv Python not found at $VENV_PYTHON — did uv sync succeed?" >&2
    exit 1
fi

# Run pip-audit from the venv.
# Use stdout redirection for JSON output (--output can be unreliable).
if [[ "${1:-}" == "--json" ]]; then
    "$VENV_PYTHON" -m pip_audit "${AUDIT_ARGS[@]}" > "$REPORT_FILE" 2>/dev/null
else
    "$VENV_PYTHON" -m pip_audit "${AUDIT_ARGS[@]}"
fi
AUDIT_EXIT=$?

if [[ "$AUDIT_EXIT" -eq 0 ]]; then
    echo "==> ✅ pip-audit passed — no fixable vulnerabilities found."
else
    echo "==> ❌ pip-audit found vulnerabilities with available fixes." >&2
    echo "    Review the report and update affected dependencies." >&2
fi

exit "$AUDIT_EXIT"