#!/usr/bin/env bash
# pnpm-audit.sh — Run pnpm audit against the locked root workspace for goblin-assistant.
#
# Usage:
#   ./scripts/security/pnpm-audit.sh              # human-readable output
#   ./scripts/security/pnpm-audit.sh --json        # JSON output (consumed by CI), written to
#                                                    # reports/security-audit-latest.json
#
# Exits 0 if no vulnerabilities at or above --audit-level are found, 1 otherwise.
# pnpm audit always exits nonzero on vulnerabilities, and nonzero on JSON output
# too, so exit codes are normalized below to match pip-audit.sh's convention.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORT_DIR="$REPO_ROOT/reports"
REPORT_FILE="$REPORT_DIR/security-audit-latest.json"
AUDIT_LEVEL="${PNPM_AUDIT_LEVEL:-low}"

mkdir -p "$REPORT_DIR"
cd "$REPO_ROOT"

if [[ "${1:-}" == "--json" ]]; then
    echo "==> Running pnpm audit --audit-level $AUDIT_LEVEL (JSON mode) → $REPORT_FILE"
    pnpm audit --audit-level "$AUDIT_LEVEL" --json > "$REPORT_FILE"
    AUDIT_EXIT=$?
else
    echo "==> Running pnpm audit --audit-level $AUDIT_LEVEL (human-readable)..."
    pnpm audit --audit-level "$AUDIT_LEVEL"
    AUDIT_EXIT=$?
fi

if [[ "$AUDIT_EXIT" -eq 0 ]]; then
    echo "==> ✅ pnpm audit passed — no vulnerabilities at or above '$AUDIT_LEVEL' found."
else
    echo "==> ❌ pnpm audit found vulnerabilities at or above '$AUDIT_LEVEL'." >&2
    echo "    Review $REPORT_FILE and update affected dependencies." >&2
fi

exit "$AUDIT_EXIT"
