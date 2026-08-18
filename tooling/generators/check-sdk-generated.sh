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

mkdir -p "$ROOT_DIR/.tmp"
SNAPSHOT_DIR="$(mktemp -d "${ROOT_DIR}/.tmp/sdk-generated-before.XXXXXX")"
trap 'rm -rf "$SNAPSHOT_DIR"' EXIT

for file in "${GENERATED_FILES[@]}"; do
  snapshot_file="$SNAPSHOT_DIR/$file"
  mkdir -p "$(dirname "$snapshot_file")"
  if [[ -f "$file" ]]; then
    cp "$file" "$snapshot_file"
  else
    touch "$snapshot_file.missing"
  fi
done

bash tooling/generators/generate-sdk-client.sh

stale=0
for file in "${GENERATED_FILES[@]}"; do
  snapshot_file="$SNAPSHOT_DIR/$file"
  if [[ -f "$snapshot_file.missing" ]]; then
    echo "Generated artifact was missing before regeneration: $file"
    stale=1
    continue
  fi
  if [[ ! -f "$file" ]]; then
    echo "Generated artifact disappeared after regeneration: $file"
    stale=1
    continue
  fi
  if ! cmp -s "$snapshot_file" "$file"; then
    echo "Generated artifact changed after regeneration: $file"
    diff -u "$snapshot_file" "$file" || true
    stale=1
  fi
done

if [[ "$stale" -ne 0 ]]; then
  echo "SDK and route generated artifacts are stale. Run: make sdk-generate"
  exit 1
fi

echo "SDK generated artifacts are up-to-date."
