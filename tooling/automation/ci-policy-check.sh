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

  # CI checkouts are often shallow. Unshallow before computing the PR range so
  # base-only commits cannot leak into the commit-policy check as disconnected
  # history. Then inspect only commits reachable from HEAD and not from base.
  if [[ "$(git rev-parse --is-shallow-repository 2>/dev/null || echo false)" == "true" ]]; then
    git fetch --unshallow origin
  fi
  git fetch origin "+refs/heads/$BASE_REF:refs/remotes/origin/$BASE_REF"
  RANGE="origin/$BASE_REF..HEAD"
else
  if git rev-parse HEAD~1 >/dev/null 2>&1; then
    RANGE="HEAD~1..HEAD"
  else
    RANGE="HEAD"
  fi
fi

# --no-merges is load-bearing, not cosmetic.
#
# On a pull_request event actions/checkout checks out refs/pull/N/merge --
# a merge commit GitHub synthesises between the PR head and the base. Its
# subject is always "Merge <sha> into <sha>", which no conventional-commit
# regex can match, so without this flag the check fails on every PR no
# matter what the author actually wrote.
#
# The two-dot PR range above is also intentional. A three-dot range on a
# shallow checkout can include the base commit when Git cannot see a merge
# base, causing an unrelated main-branch subject to fail the PR.
#
# Regression coverage: tooling/automation/tests/test-ci-policy-check.sh
COMMITS=$(git log --no-merges --format=%s $RANGE)
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
