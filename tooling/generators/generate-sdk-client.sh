#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3.11 tooling/generators/export-openapi.py
python3.11 tooling/generators/export-route-manifest.py
mkdir -p packages/sdk/src/generated
mkdir -p .tmp
TMPDIR="$ROOT_DIR/.tmp" pnpm --filter @goblin/web exec openapi-typescript \
  ../../packages/sdk/openapi/openapi.json \
  -o ../../packages/sdk/src/generated/openapi.ts

python3 tooling/generators/split-sdk.py
python3.11 tooling/generators/generate-api-route-inventory.py

echo "Generated SDK schema, route manifest, inventory, and TypeScript types."
