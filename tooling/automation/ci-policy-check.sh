#!/usr/bin/env bash
set -euo pipefail

BRANCH_REGEX='^(feature|fix|refactor|infra)/'
COMMIT_REGEX='^(feat|fix|refactor|infra|chore|docs|test|build|ci|perf|revert)(\([a-z0-9._/-]+\))?: .+'

EVENT_NAME="${GITHUB_EVENT_NAME:-}"
HEAD_BRANCH="${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-}}"

if [[ -z "$HEAD_BRANCH" ]]; then
  echo "Could not determine branch name from GitHub environment."
  exit 1
fi

if [[ "$EVENT_NAME" == "pull_request" ]]; then
  if [[ ! "$HEAD_BRANCH" =~ $BRANCH_REGEX ]]; then
    echo "Invalid branch name '$HEAD_BRANCH'. Expected pattern: $BRANCH_REGEX"
    exit 1
  fi
fi

if [[ "$EVENT_NAME" == "pull_request" ]]; then
  BASE_REF="${GITHUB_BASE_REF:-main}"
  git fetch origin "$BASE_REF" --depth=1
  RANGE="origin/$BASE_REF...HEAD"
else
  if git rev-parse HEAD~1 >/dev/null 2>&1; then
    RANGE="HEAD~1..HEAD"
  else
    RANGE="HEAD"
  fi
fi

COMMITS=$(git log --format=%s $RANGE)
if [[ -z "$COMMITS" ]]; then
  echo "No commit subjects found in range $RANGE"
  exit 1
fi

while IFS= read -r subject; do
  if [[ ! "$subject" =~ $COMMIT_REGEX ]]; then
    echo "Invalid commit subject: '$subject'"
    echo "Expected conventional format, e.g. feat(sandbox): add timeout enforcement"
    exit 1
  fi
done <<< "$COMMITS"

echo "Policy checks passed: branch naming and conventional commits."

python3 tooling/automation/check-structure-policy.py --range "$RANGE"
