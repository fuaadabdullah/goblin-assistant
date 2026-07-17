#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

bash tooling/generators/generate-sdk-client.sh

GENERATED_FILES=(
  packages/shared/src/generated/api-proxy-routes.ts
  packages/shared/src/constants/routes.ts
  packages/shared/src/generated/api-route-paths.ts
  packages/sdk/openapi/openapi.json
  packages/sdk/openapi/routes.json
  packages/sdk/src/generated/openapi.ts
  packages/sdk/src/generated/components.ts
  packages/sdk/src/generated/operations.ts
  packages/sdk/src/generated/paths.ts
  docs/backend/API_ROUTE_INVENTORY.generated.md
)

if ! git diff --quiet -- "${GENERATED_FILES[@]}"; then
  echo "SDK and route generated artifacts are stale. Run: make sdk-generate"
  git --no-pager diff -- "${GENERATED_FILES[@]}"
  exit 1
fi

echo "SDK generated artifacts are up-to-date."
