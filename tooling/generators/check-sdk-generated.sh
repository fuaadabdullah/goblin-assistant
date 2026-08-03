#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

GENERATED_FILES=(
  packages/shared/src/generated/api-proxy-routes.ts
  packages/shared/src/constants/routes.ts
  packages/shared/src/generated/api-route-paths.ts
  packages/sdk/openapi/openapi.json
  packages/sdk/openapi/routes.json
  packages/sdk/src/generated/components.ts
  packages/sdk/src/generated/operations.ts
  packages/sdk/src/generated/paths.ts
  docs/backend/API_ROUTE_INVENTORY.generated.md
)

hash_generated_files() {
  local file
  for file in "${GENERATED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
      printf '%s\t%s\n' "$file" "$(git hash-object "$file")"
    else
      printf '%s\tMISSING\n' "$file"
    fi
  done
}

CHECK_DIR="$(mktemp -d)"
trap 'rm -rf -- "$CHECK_DIR"' EXIT
hash_generated_files > "$CHECK_DIR/before"
bash tooling/generators/generate-sdk-client.sh
hash_generated_files > "$CHECK_DIR/after"

if ! diff -u "$CHECK_DIR/before" "$CHECK_DIR/after"; then
  echo "SDK and route generated artifacts are stale. Run: make sdk-generate"
  git --no-pager diff -- "${GENERATED_FILES[@]}"
  exit 1
fi

echo "SDK generated artifacts are up-to-date."
