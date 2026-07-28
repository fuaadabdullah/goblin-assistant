# Goblin Assistant — Engineering Guidelines

## State Management

| State type | Tool | Rule |
|---|---|---|
| **Server state** (API responses, queries, mutations) | React Query (`@tanstack/react-query`) | All server data lives in `useQuery` / `useMutation`. Never mirror server state into Zustand or `useState`. |
| **Local UI state** (modals, sidebars, toasts, theme) | Zustand (`useUIStore` in `src/store/uiStore.ts`) | No React Context for UI state. Context is reserved for global app context only. |
| **Global app context** (provider registry, contrast mode) | React Context | Only for values that are structurally impossible to express in Zustand (e.g. a context that must wrap a subtree). |

### Query keys

All React Query keys are defined in `src/lib/query-keys.ts`. Never use bare string arrays (`['myKey']`) inline in a component — add a named entry to `queryKeys` instead.

### Auth state

Auth is the one intentional exception where Zustand and React Query both hold auth data:
- `useAuthStore` (Zustand) — bootstrap source, hydrated from cookies/localStorage on app load
- `useAuthSession` (React Query, key `queryKeys.authValidate`) — server validation of the stored token

`useAuthStore` is the write path (login/logout). React Query is the read-validation path. They are kept in sync by `bootstrapAuthSession`.

## API Client

All API calls go through `apiClient` from `@/lib/api`. Do not call `fetch`/`axios` directly in components or hooks.

## Frontend architecture

```
app/          Next.js app router pages (thin shells — one line each)
src/
  components/ Shared UI components
  features/   Domain features (chat, admin, search, sandbox …)
  hooks/      Shared custom hooks (useToast, useContrastMode …)
  screens/    Full-page screen components used by app/ pages
  store/      Zustand stores (uiStore, authStore)
  lib/        apiClient, queryClient, queryKeys, shared utilities
  contexts/   React Context providers (ProviderContext, ContrastModeContext)
```
