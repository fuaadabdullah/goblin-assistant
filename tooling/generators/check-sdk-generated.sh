#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

bash tooling/generators/generate-sdk-client.sh

if ! git diff --quiet -- packages/sdk/openapi/openapi.json packages/sdk/src/generated/openapi.ts; then
  echo "SDK generated artifacts are stale. Run: make sdk-generate"
  git --no-pager diff -- packages/sdk/openapi/openapi.json packages/sdk/src/generated/openapi.ts
  exit 1
fi

echo "SDK generated artifacts are up-to-date."
