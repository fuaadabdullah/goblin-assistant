#!/usr/bin/env bash
#
# Regression tests for tooling/automation/ci-policy-check.sh.
#
# These build throwaway git repositories and run the real checker against
# them, so the assertions are about observed behaviour rather than a
# re-implementation of the regexes.
#
# The case that matters most is "ignores synthetic merge commits". On a
# pull_request event actions/checkout checks out refs/pull/N/merge, a merge
# commit GitHub creates between the PR head and the base, whose subject is
# always "Merge <sha> into <sha>". That subject cannot satisfy a
# conventional-commit regex, so before --no-merges the policy job failed on
# every pull request ever opened against this repo. If someone later
# "tidies up" that flag, this file is what stops it shipping.
#
#   bash tooling/automation/tests/test-ci-policy-check.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="$REPO_ROOT/tooling/automation/ci-policy-check.sh"

if [[ ! -f "$SCRIPT" ]]; then
  echo "cannot find ci-policy-check.sh at $SCRIPT"
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# The checker ends by invoking `python3 check-structure-policy.py`. These
# tests are about branch and commit-subject rules, so shim python3 to a
# no-op and put it first on PATH. That also keeps the suite hermetic on
# Windows, where a bare `python3` hits the Microsoft Store alias stub and
# exits 49 regardless of what the policy check decided.
SHIM="$WORK/bin"
mkdir -p "$SHIM"
printf '#!/usr/bin/env bash\nexit 0\n' > "$SHIM/python3"
chmod +x "$SHIM/python3"
export PATH="$SHIM:$PATH"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Build a repo with a real origin, so the script's `git fetch origin <base>`
# behaves the way it does in CI.
#
# $1 destination, $2.. commit subjects to place on the feature branch.
# ---------------------------------------------------------------------------
make_repo() {
  local dir="$1"; shift
  local upstream="$dir/upstream" work="$dir/work"

  mkdir -p "$upstream" "$work"
  git init --quiet --bare "$upstream"
  git init --quiet --initial-branch=main "$work"

  (
    cd "$work"
    git config user.email "test@example.com"
    git config user.name "Policy Test"
    git config commit.gpgsign false
    git config core.autocrlf false

    # The checker shells out to the structure policy at the end; stub it so
    # these tests stay focused on branch and commit-subject rules.
    mkdir -p tooling/automation
    cp "$SCRIPT" tooling/automation/ci-policy-check.sh
    printf 'import sys\nsys.exit(0)\n' > tooling/automation/check-structure-policy.py

    echo base > file.txt
    git add -A
    git commit --quiet -m "chore: base commit"

    git remote add origin "$upstream"
    git push --quiet origin main
    git fetch --quiet origin main

    git checkout --quiet -b feature/example
    local n=0
    for subject in "$@"; do
      n=$((n + 1))
      echo "change $n" >> file.txt
      git add -A
      git commit --quiet -m "$subject"
    done
  )
  echo "$work"
}

# Run the checker as GitHub Actions would for a pull_request.
run_as_pr() {
  local work="$1" branch="$2"
  (
    cd "$work"
    GITHUB_EVENT_NAME=pull_request \
    GITHUB_HEAD_REF="$branch" \
    GITHUB_BASE_REF=main \
    bash tooling/automation/ci-policy-check.sh 2>&1
  )
}

assert() {
  local name="$1" expected_rc="$2" actual_rc="$3" output="$4"
  if [[ "$expected_rc" == "$actual_rc" ]]; then
    echo "  PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $name (expected exit $expected_rc, got $actual_rc)"
    echo "        output: $(echo "$output" | tail -3 | tr '\n' ' ')"
    FAIL=$((FAIL + 1))
  fi
}

echo "ci-policy-check.sh regression tests"
echo

# --- 1. conventional commits are accepted ---------------------------------
work="$(make_repo "$WORK/ok" "feat(nodes): add a thing" "fix(api): correct a thing")"
out="$(run_as_pr "$work" feature/example)"; rc=$?
assert "accepts conventional commit subjects" 0 "$rc" "$out"

# --- 2. non-conventional commits are rejected ------------------------------
work="$(make_repo "$WORK/bad" "feat(nodes): fine subject" "Add a thing without a type")"
out="$(run_as_pr "$work" feature/example)"; rc=$?
assert "rejects a non-conventional commit subject" 1 "$rc" "$out"
if [[ "$out" != *"Invalid commit subject"* ]]; then
  echo "  FAIL  rejection names the offending subject"
  FAIL=$((FAIL + 1))
else
  echo "  PASS  rejection names the offending subject"
  PASS=$((PASS + 1))
fi

# --- 3. synthetic merge commits are ignored --------------------------------
# Reproduces refs/pull/N/merge: check out the base and merge the PR head with
# GitHub's generated subject, then run the checker from that detached commit.
work="$(make_repo "$WORK/merge" "feat(nodes): add a thing")"
(
  cd "$work"
  head_sha="$(git rev-parse HEAD)"
  base_sha="$(git rev-parse main)"
  git checkout --quiet main
  git merge --quiet --no-ff --no-commit "$head_sha" >/dev/null 2>&1 || true
  git commit --quiet --no-verify -m "Merge $head_sha into $base_sha"
) >/dev/null 2>&1
out="$(run_as_pr "$work" feature/example)"; rc=$?
assert "ignores GitHub's synthetic merge commit" 0 "$rc" "$out"
if [[ "$out" == *"Merge "*"into"* ]]; then
  echo "  FAIL  merge subject must not be evaluated"
  FAIL=$((FAIL + 1))
else
  echo "  PASS  merge subject is not evaluated"
  PASS=$((PASS + 1))
fi

# --- 4. branch naming is still enforced ------------------------------------
work="$(make_repo "$WORK/branch" "feat(nodes): add a thing")"
(cd "$work" && git branch --quiet -m feature/example feat/example)
out="$(run_as_pr "$work" feat/example)"; rc=$?
assert "rejects a branch name outside the allowed prefixes" 1 "$rc" "$out"

work="$(make_repo "$WORK/branch-ok" "feat(nodes): add a thing")"
(cd "$work" && git branch --quiet -m feature/example fix/example)
out="$(run_as_pr "$work" fix/example)"; rc=$?
assert "accepts an allowed branch prefix" 0 "$rc" "$out"

echo
echo "passed: $PASS   failed: $FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
echo "ci-policy-check.sh behaves as documented."
