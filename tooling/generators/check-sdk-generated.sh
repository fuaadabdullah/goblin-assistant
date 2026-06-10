#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

bash tooling/generators/generate-sdk-client.sh

GENERATED_FILES=(
  packages/sdk/openapi/openapi.json
  packages/sdk/src/generated/openapi.ts
  packages/sdk/src/generated/components.ts
  packages/sdk/src/generated/operations.ts
  packages/sdk/src/generated/paths.ts
)

if ! git diff --quiet -- "${GENERATED_FILES[@]}"; then
  echo "SDK generated artifacts are stale. Run: make sdk-generate"
  git --no-pager diff -- "${GENERATED_FILES[@]}"
  exit 1
fi

echo "SDK generated artifacts are up-to-date."
