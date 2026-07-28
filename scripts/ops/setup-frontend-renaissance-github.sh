#!/bin/bash

set -euo pipefail

REPO="${1:-fuaadabdullah/goblin-assistant}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required: https://cli.github.com/"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Please authenticate first: gh auth login"
  exit 1
fi

echo "Configuring Frontend Renaissance labels for ${REPO}..."

gh label create "area:design-system" --repo "$REPO" --color "0E8A16" --description "Frontend Renaissance - Design System" --force
gh label create "area:workspace-shell" --repo "$REPO" --color "1D76DB" --description "Frontend Renaissance - Workspace Shell" --force
gh label create "area:chat-ux" --repo "$REPO" --color "B60205" --description "Frontend Renaissance - Chat UX" --force
gh label create "area:operations" --repo "$REPO" --color "5319E7" --description "Frontend Renaissance - Operations" --force
gh label create "type:slice" --repo "$REPO" --color "FBCA04" --description "Single feature slice PR" --force
gh label create "status:blocked" --repo "$REPO" --color "D93F0B" --description "Blocked work item" --force

echo "Ensuring Frontend Renaissance milestones exist..."

ensure_milestone() {
  local title="$1"
  local description="$2"
  if gh api "repos/${REPO}/milestones?state=all&per_page=100" --jq ".[] | select(.title == \"${title}\") | .number" | grep -q .; then
    echo "Milestone exists: ${title}"
  else
    gh api "repos/${REPO}/milestones" \
      --method POST \
      --field title="$title" \
      --field description="$description" >/dev/null
    echo "Created milestone: ${title}"
  fi
}

ensure_milestone "M1 Design System" "Frontend Renaissance milestone 1: Design System"
ensure_milestone "M2 Workspace" "Frontend Renaissance milestone 2: Workspace"
ensure_milestone "M3 Chat" "Frontend Renaissance milestone 3: Chat"
ensure_milestone "M4 Dashboard" "Frontend Renaissance milestone 4: Dashboard"
ensure_milestone "M5 Polish" "Frontend Renaissance milestone 5: Polish"
ensure_milestone "M6 Launch" "Frontend Renaissance milestone 6: Launch"

echo "Applying branch protection for main..."
bash scripts/setup-branch-protection.sh

echo "Frontend Renaissance GitHub setup complete."