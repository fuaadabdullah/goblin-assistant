#!/usr/bin/env bash
set -euo pipefail

staged_files="$(git diff --cached --name-only --diff-filter=ACMR)"
if [ -z "$staged_files" ]; then
  exit 0
fi

blocked_files=()
while IFS= read -r file; do
  [ -z "$file" ] && continue
  case "$file" in
    goblin_assistant.db|*.sqlite|*.sqlite3|*.db)
      blocked_files+=("$file")
      ;;
  esac
done <<< "$staged_files"

if [ ${#blocked_files[@]} -eq 0 ]; then
  exit 0
fi

echo "❌ Commit blocked: SQLite/database artifact(s) detected in staged changes."
echo ""
echo "Blocked files:"
for file in "${blocked_files[@]}"; do
  echo "  - $file"
done

echo ""
echo "Remediation:"
echo "  git rm --cached <file>"
echo "  # or unstage all DB artifacts"
echo "  git restore --staged $(printf '%q ' "${blocked_files[@]}")"

exit 1
