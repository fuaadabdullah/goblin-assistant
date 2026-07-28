# ADR-0006: Supabase-Only Authentication

## Status
accepted

## Date
2026-07-17

## Context
The production frontend already uses Supabase as the active browser auth path, and the shared HTTP client injects Supabase access tokens into backend requests. The legacy backend Google/passkey flow is no longer the canonical production route and should not be revived as a parallel auth system.

## Decision
Keep authentication Supabase-only.

- The backend settings API is protected by the existing `get_current_user` dependency rather than a new session model or proxy-backed auth path.
- The legacy backend Google/passkey flow remains deprecated dead code and is not a restoration target.
- The frontend auth bootstrap and backend API client stay on the existing Supabase bearer-token path.

## Consequences
- Production auth remains single-source and easier to reason about.
- No second cookie/session transport is introduced.
- Future auth changes should migrate fully to a new canonical system rather than layering hybrid behavior on top of Supabase.

## Operational Notes
- Keep the browser auth dashboard configuration aligned with the Supabase provider settings used in production.
- Do not reintroduce backend OAuth proxying or cookie-based hybrid auth in the Next.js layer.
- If auth requirements change materially, write a new ADR before changing the production auth boundary.
