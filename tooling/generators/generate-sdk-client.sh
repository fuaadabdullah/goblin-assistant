#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3.11 tooling/generators/export-openapi.py
mkdir -p packages/sdk/src/generated
mkdir -p .tmp
TMPDIR="$ROOT_DIR/.tmp" pnpm --filter @goblin/web exec openapi-typescript \
  ../../packages/sdk/openapi/openapi.json \
  -o ../../packages/sdk/src/generated/openapi.ts

echo "Generated SDK schema and TypeScript types."
