#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON:-python3.11}"
NODE_BIN="${NODE:-node}"
export NODE="$NODE_BIN"
export PYTHONUTF8="${PYTHONUTF8:-1}"

bash tooling/generators/require-supported-node.sh

if [[ -n "${PNPM_CLI:-}" ]]; then
  PNPM_COMMAND=("$NODE_BIN" "$PNPM_CLI")
else
  PNPM_COMMAND=(pnpm)
fi

"$PYTHON_BIN" tooling/generators/generate-shared-api-routes.py
"$PYTHON_BIN" tooling/generators/export-openapi.py
"$PYTHON_BIN" tooling/generators/export-route-manifest.py
"$PYTHON_BIN" tooling/generators/generate-shared-api-proxy-routes.py
"$PYTHON_BIN" tooling/generators/generate-shared-api-route-types.py
mkdir -p packages/sdk/src/generated
mkdir -p .tmp
TMPDIR="$ROOT_DIR/.tmp" "${PNPM_COMMAND[@]}" --filter @goblin/web exec openapi-typescript \
  ../../packages/sdk/openapi/openapi.json \
  -o ../../.tmp/openapi-typescript-output.ts

"$PYTHON_BIN" tooling/generators/split-sdk.py
"$PYTHON_BIN" tooling/generators/generate-api-route-inventory.py

echo "Generated shared route contracts, SDK schema, route manifest, inventory, and TypeScript types."
