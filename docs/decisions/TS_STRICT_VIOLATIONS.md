# TypeScript Hardening: `noUncheckedIndexedAccess` Violation Tracking

## Status: RESOLVED ✅

**Date Enabled:** 2026-06-06  
**Config File:** All 6 tsconfig files in the project  
**Initial Baseline Errors:** 39  
**Current Errors:** 0  

## Summary

Enabled `noUncheckedIndexedAccess: true` across all TypeScript projects:
- `apps/web/tsconfig.json`
- `packages/shared/tsconfig.json`
- `packages/types/tsconfig.json`
- `packages/config/tsconfig.json`
- `packages/sdk/tsconfig.json`
- `packages/ui/tsconfig.json`

## Fix Strategy

All violations were fixed using the following patterns:

1. **Non-null assertion (`!`)** — Used where the index is provably in-bounds (e.g., modulo-guarded access, length-checked arrays). Most common fix.
2. **Optional chaining / nullish coalescing (`?.` / `??`)** — Used where graceful fallback is needed.
3. **Local variable aliasing** — Used for repeated indexed access to avoid repeating the non-null assertion.
4. **Immediately-invoked function expressions (IIFE)** — Used in JSX to narrow types with early returns.

## Files Modified (23 files)

| File | Fix Type |
|------|----------|
| `apps/web/src/components/auth/AuthPrompt.tsx` | `!` assertion on focusable elements |
| `apps/web/src/components/auth/ModularLoginForm.tsx` | (fixed via turnstile.ts) |
| `apps/web/src/components/cost/CostBreakdownChart.tsx` | `!` assertion on payload[0] |
| `apps/web/src/components/cost/ProviderUsageChart.tsx` | `!` assertion on payload[0] |
| `apps/web/src/components/cost/chartPalette.ts` | `!` assertion on palette array |
| `apps/web/src/components/Seo.tsx` | `!` assertion on string split results |
| `apps/web/src/config/turnstile.ts` | Typed Record keys + `!` assertion |
| `apps/web/src/features/admin/providers/components/ProviderSidebar.tsx` | Local variable narrowing via IIFE |
| `apps/web/src/features/chat/api/index.ts` | `!` assertion on split/array lines |
| `apps/web/src/features/chat/components/ChatMessageList.tsx` | `!` assertion on filtered array |
| `apps/web/src/features/chat/components/MessageMarkdown.tsx` | `?? null` fallback for regex match |
| `apps/web/src/features/chat/hooks/useChatSession.ts` | `!` assertion on threads[0] |
| `apps/web/src/features/chat/hooks/useMessages/useRegenerateMessage.ts` | `!` assertion on messages[]. |
| `apps/web/src/features/onboarding/ControlPanelHero.tsx` | `!` assertion on words[index] |
| `apps/web/src/features/onboarding/HomeScreen.tsx` | `!` assertion on const array |
| `apps/web/src/features/onboarding/OnboardingWizard.tsx` | `!` assertion + optional chaining |
| `apps/web/src/features/search/hooks/useSearchResults.ts` | `!` assertion on collections[0] |
| `apps/web/src/hooks/useContrastMode.tsx` | `!` assertion on MODE_CYCLE |
| `apps/web/src/hooks/useFocusTrap.ts` | `!` assertion on focusable elements |
| `apps/web/src/hooks/useProviderSelection.ts` | `!` assertion on providers[0] |
| `apps/web/src/lib/chat-history.ts` | `!` assertion on threads[0] |
| `apps/web/src/screens/Dashboard.tsx` | (fixed via chartPalette.ts) |
| `apps/web/src/screens/GoblinDemo.tsx` | Local variable narrowing via IIFE |
| `apps/web/src/services/provider-router.ts` | Local variable aliasing |

## Pre-existing `@ts-expect-error` Comments: 7

These are tracked but not related to `noUncheckedIndexedAccess`. They should be resolved independently.

## Regression Guard

A regression guard is in place via `make type-check`. The CI pipeline runs this target; any new violations will fail the build.