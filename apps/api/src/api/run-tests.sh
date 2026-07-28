#!/bin/bash
# Run API tests with temp/cache paths scoped to this checkout.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TMPDIR="${TMPDIR:-$API_ROOT/.tmp/pip}"
mkdir -p "$TMPDIR"
export TMPDIR
export PYTHONDONTWRITEBYTECODE=1

# Default to running all tests if no arguments provided
PYTEST_ARGS="${@:-.}"

echo "Running API tests with checkout-local temp/cache paths..."
echo "TMPDIR: $TMPDIR"
echo "PYTHONDONTWRITEBYTECODE: $PYTHONDONTWRITEBYTECODE"
echo "Cache dir: $API_ROOT/.pytest_cache (configured in pyproject.toml)"
echo ""

cd "$SCRIPT_DIR"
pytest $PYTEST_ARGS
