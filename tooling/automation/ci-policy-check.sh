#!/usr/bin/env bash
set -euo pipefail

BRANCH_REGEX='^(feature|fix|refactor|infra)/'
COMMIT_REGEX='^(feat|fix|refactor|infra|chore|docs|test|build|ci|perf|revert|style|deps|release|security)(\([a-z0-9._/ -]+\))?: .+'

# Support both GitHub Actions and CircleCI environments
if [[ -n "${GITHUB_EVENT_NAME:-}" ]]; then
  EVENT_NAME="${GITHUB_EVENT_NAME}"
  HEAD_BRANCH="${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-}}"
elif [[ -n "${CIRCLE_BRANCH:-}" ]]; then
  HEAD_BRANCH="${CIRCLE_BRANCH}"
  # CircleCI sets CIRCLE_PULL_REQUEST when building a PR
  EVENT_NAME="${CIRCLE_PULL_REQUEST:+pull_request}"
  EVENT_NAME="${EVENT_NAME:-push}"
else
  # Local or unknown CI — use git
  HEAD_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  EVENT_NAME="push"
fi

if [[ -z "$HEAD_BRANCH" ]]; then
  echo "Could not determine branch name from CI environment."
  exit 1
fi

TRUNK_REGEX='^(main|master|develop|reorg/.+)$'
if [[ "$EVENT_NAME" == "pull_request" && ! "$HEAD_BRANCH" =~ $TRUNK_REGEX ]]; then
  if [[ ! "$HEAD_BRANCH" =~ $BRANCH_REGEX ]]; then
    echo "Invalid branch name '$HEAD_BRANCH'. Expected pattern: $BRANCH_REGEX"
    exit 1
  fi
fi

if [[ "$EVENT_NAME" == "pull_request" && ! "$HEAD_BRANCH" =~ $TRUNK_REGEX ]]; then
  BASE_REF="${GITHUB_BASE_REF:-${CIRCLE_TARGET_BRANCH:-main}}"
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
