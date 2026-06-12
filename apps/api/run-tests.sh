#!/bin/bash
# Run tests using GOBLINOS drive for temp/cache to avoid local disk space issues

export TMPDIR='/Volumes/GOBLINOS 1/apps/.tmp/pip'
export PYTHONDONTWRITEBYTECODE=1

# Default to running all tests if no arguments provided
PYTEST_ARGS="${@:-.}"

echo "Running tests with GOBLINOS drive for temp/cache..."
echo "TMPDIR: $TMPDIR"
echo "PYTHONDONTWRITEBYTECODE: $PYTHONDONTWRITEBYTECODE"
echo "Cache dir: /Volumes/GOBLINOS 1/apps/.tmp/pytest_cache (configured in pytest.ini)"
echo ""

cd "$(dirname "$0")"
pytest $PYTEST_ARGS
