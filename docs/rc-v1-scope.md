# rc/v1 — Release Candidate Scope

The `rc/v1` branch is frozen for feature development. Its only job is to ship
a stable v1. Everything that goes in must make v1 more correct, more secure,
or easier to operate. Nothing goes in because it would be cool.

---

## What is allowed

| Category | Criteria |
|---|---|
| **Bug fix** | Something is broken in the current code. Has a repro. Fix is scoped to the broken path. |
| **Performance fix** | Measured regression or a known hot path with a concrete improvement. No speculative optimization. |
| **Security fix** | CVE, credential exposure, auth bypass, injection surface, or unsafe dependency. Gets fast-tracked regardless of freeze. |
| **UX blocker** | A user cannot complete a core flow. Not "this could be smoother" — the flow is broken or inaccessible. |
| **Missing test** | A critical path has no coverage. Write the test, nothing else. No refactoring the code under test. |
| **Operational docs** | A runbook, env var reference, or deploy guide that is required to run the system. Not architecture notes or future plans. |

---

## What is blocked

- New AI providers or model integrations
- New API endpoints or response fields (unless they fix a blocker)
- New UI features, screens, or components
- Refactors (even good ones — they belong on main after v1 ships)
- New dependencies
- "This would be sick" ideas — write them down elsewhere, open against main after the release

---

## Decision process for borderline changes

Ask these questions in order. Stop at the first **No**.

1. Does this fix something that is demonstrably broken or dangerous **today**?
2. Is the fix scoped to the minimum change needed to unblock v1?
3. Would skipping this change mean v1 ships with a known defect, security hole, or operational gap?

All three must be **Yes**. If you're unsure, the answer is No — note it and open it against `main` after the release.

---

## Branch rules

- Base: `reorg/monorepo-visibility` at the point `rc/v1` was cut
- Merging into `rc/v1`: requires a PR; no direct pushes
- Merging back to `main`: `rc/v1` gets squash-merged to `reorg/monorepo-visibility` when the release ships; any fixes land on main at that point
- `feat/*` branches: do NOT merge new feature branches into `rc/v1`; cherry-pick specific bug-fix commits if needed

---

## What ships in v1

Minimum viable scope (non-negotiable):

- [ ] Chat with context assembly (long-term + semantic layers)
- [ ] Provider dispatch with fallback
- [ ] Auth (login, session validation, logout)
- [ ] Conversation archiving
- [ ] Sandbox worker (isolated execution)
- [ ] Settings (provider key status, user preferences)
- [ ] Operational runbooks for deploy, DB migration, provider config

---

*Freeze date: 2026-08-18. Lifted when the release ships or the team explicitly votes to widen scope.*
