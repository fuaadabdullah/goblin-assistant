#!/usr/bin/env python3
"""AI code review script — called by .github/workflows/pr-review.yml."""

import os
import sys

import anthropic

MAX_DIFF_CHARS = 80_000  # ~20k tokens; keeps cost predictable on large PRs

SYSTEM_PROMPT = """\
You are a senior engineer reviewing a pull request for a TypeScript/React + Python/FastAPI monorepo.

Review the diff for the following categories — only surface findings that are real issues:

1. **Type errors** — missing type annotations, `any` abuse, incorrect generics, wrong async/await usage
2. **Dead code** — unused imports, unreachable branches, variables declared but never read
3. **Obvious bugs** — off-by-one errors, null/undefined dereferences, mutation of shared state, \
promise not awaited
4. **Security** — SQL injection, XSS, hardcoded secrets, insecure API calls
5. **Project conventions** — React Query (`useQuery`/`useMutation`) for all server state, \
`apiClient` from `@/lib/api` for all HTTP calls (never raw fetch/axios in components), \
query keys from `queryKeys` in `src/lib/query-keys.ts` (no inline string arrays)

Format your response as Markdown:
- First line MUST be exactly: `<!-- ai-review-comment -->`
- Second line: one-sentence summary of the overall PR
- One `##` section per category that has findings; omit empty categories entirely
- Each finding: file path + line reference if available, then a concise explanation
- Final line: `✅ LGTM` if no significant issues were found

Be concise. Do not comment on style preferences, naming conventions, or things that are already \
caught by the linter. Only flag things a human reviewer would block on.\
"""


def truncate_diff(diff: str) -> str:
    if len(diff) <= MAX_DIFF_CHARS:
        return diff
    return diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated — showing first 80k characters]"


def build_user_message(diff: str) -> str:
    title = os.environ.get("GITHUB_PR_TITLE", "").strip()
    body = os.environ.get("GITHUB_PR_BODY", "").strip()

    parts = []
    if title:
        parts.append(f"**PR title:** {title}")
    if body:
        parts.append(f"**PR description:**\n{body}")
    parts.append(f"```diff\n{truncate_diff(diff)}\n```")

    return "\n\n".join(parts)


def review(diff: str) -> str:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(diff)}],
    )

    return message.content[0].text


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: ai_review.py <diff_file>", file=sys.stderr)
        sys.exit(1)

    diff_path = sys.argv[1]
    with open(diff_path) as f:
        diff = f.read()

    if not diff.strip():
        print("<!-- ai-review-comment -->\n_No diff to review._")
        return

    print(review(diff))


if __name__ == "__main__":
    main()
