#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK_SCRIPT="$ROOT_DIR/scripts/git-hooks/check-no-sqlite-in-commit.sh"

tmp_base="${TMPDIR:-}"
if [ -z "$tmp_base" ] || [ ! -w "$tmp_base" ]; then
  tmp_base="$ROOT_DIR/.tmp"
fi
mkdir -p "$tmp_base"
workdir="$(mktemp -d "$tmp_base/sqlite-hook-test.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT

pushd "$workdir" >/dev/null
git init -q
git config user.email "test@example.com"
git config user.name "Test User"

printf 'ok\n' > ok.txt
git add ok.txt

if ! "$HOOK_SCRIPT" >/dev/null 2>&1; then
  echo "Expected hook to allow non-database files"
  exit 1
fi

printf 'journal\n' > artifact.db-journal
git add artifact.db-journal

if output="$("$HOOK_SCRIPT" 2>&1)"; then
  echo "Expected hook to block db-journal files"
  exit 1
fi

case "$output" in
  *"artifact.db-journal"*) ;;
  *)
    echo "Hook output did not mention the blocked journal file"
    echo "$output"
    exit 1
    ;;
esac

popd >/dev/null

echo "SQLite hook regression test passed"