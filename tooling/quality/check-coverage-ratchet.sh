#!/usr/bin/env bash
# Coverage ratchet: apps/api/coverage-baseline.txt may only go up.
#
# The backend gate (make test-api-coverage, CircleCI test-backend) fails
# under this floor. The long-term target is 80%; raise the baseline whenever
# coverage improves, and never lower it to get a red build green.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASELINE_FILE="apps/api/coverage-baseline.txt"
BASE_REF="${GITHUB_BASE_REF:-${CIRCLE_TARGET_BRANCH:-main}}"

current="$(tr -d '[:space:]' < "$BASELINE_FILE")"
if ! [[ "$current" =~ ^[0-9]+$ ]] || (( current < 0 || current > 100 )); then
  echo "$BASELINE_FILE must hold a whole percentage (0-100), got '$current'."
  exit 1
fi

pyproject_floor="$(sed -n 's/^fail_under = \([0-9]*\)$/\1/p' apps/api/pyproject.toml)"
if [[ "$pyproject_floor" != "$current" ]]; then
  echo "apps/api/pyproject.toml fail_under ($pyproject_floor) must equal $BASELINE_FILE ($current)."
  exit 1
fi

git fetch --quiet origin "$BASE_REF" --depth=1 2>/dev/null || true
previous="$(git show "origin/$BASE_REF:$BASELINE_FILE" 2>/dev/null | tr -d '[:space:]' || true)"
if [[ -z "$previous" ]]; then
  echo "No coverage baseline on origin/$BASE_REF yet; accepting $current%."
  exit 0
fi

if (( current < previous )); then
  echo "Coverage baseline lowered from $previous% to $current%. The ratchet only goes up."
  exit 1
fi

echo "Coverage baseline $current% (origin/$BASE_REF: $previous%)."
