# Copilot Instructions

These rules apply to GitHub Copilot and any other coding agent working in this repo. They complement [AGENTS.md](../AGENTS.md), which is the canonical map of where code lives and which commands to run.

## Always add tests with your changes

Every code change must ship with tests in the same PR. No exceptions for "small" changes — small changes are exactly the ones that regress silently.

- **New function or endpoint:** add a unit test covering the happy path and at least one edge case (auth failure, missing input, empty result, etc.).
- **Bug fix:** add a test that fails on `main` and passes with your fix. This proves the fix works and prevents regression.
- **Refactor:** existing tests should still pass; if coverage was thin, add tests before refactoring so behavior is pinned down.
- **UI change:** add a component test that asserts the new behavior (rendered text, click handler, prop passthrough). For visual-only changes, note in the PR that no test was added and why.

Test locations follow the existing patterns:
- Backend: `apps/api/src/api/tests/test_*.py` — use the fixtures in `conftest.py` and `test_chat_router_core.py` (`mock_user`, `app`, `client`).
- Frontend hooks: `apps/web/src/features/*/hooks/__tests__/*.test.ts` — mock the API client and use `renderHook` + `act`.
- Frontend components: `apps/web/src/features/*/components/__tests__/*.test.tsx`.
- Shared utilities: colocated `__tests__/` directories.

Run before opening a PR:
- `make test-api` for backend changes.
- `make test-web` for frontend changes.
- `make type-check` to catch TS / mypy regressions.

## Fix existing errors you come across

If you touch a file and notice pre-existing errors — TS type errors, lint warnings, broken imports, dead code, failing tests — fix them in the same PR. Don't leave a `// TODO` or pretend you didn't see them.

Scope guidance:
- **In-file errors:** always fix. If you edited the file at all, you own its cleanliness.
- **Adjacent-file errors** (same module/feature): fix if the fix is small and obvious. If it requires real investigation or a separate design decision, open a follow-up issue and link it from the PR.
- **Repo-wide errors:** don't try to fix everything in one PR. File an issue with a punch list.

A clean checkpoint:
- `make type-check` passes with zero errors before you commit.
- `make lint` passes with zero new warnings.
- If you fix an error that wasn't yours, mention it in the PR description so reviewers know the diff is wider than the headline change.

## Other expectations

- Keep changes minimal and focused. Don't add abstractions, refactors, or "while we're here" cleanups beyond what the task requires.
- Don't add comments that restate the code. Only comment when the *why* is non-obvious.
- Don't add backwards-compatibility shims for code you control. If a function is unused after your change, delete it.
- Follow the repo structure in [AGENTS.md](../AGENTS.md) — app-local code stays in its app; cross-app contracts go in `packages/shared`.
- For UI changes, verify in the browser before claiming the task is done. Type-checks and unit tests don't catch broken styles or wrong wiring.
