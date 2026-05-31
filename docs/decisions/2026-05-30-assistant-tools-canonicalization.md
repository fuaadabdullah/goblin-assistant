# Assistant Tools Canonicalization (2026-05-30)

## Decision

`apps/api/src/api/assistant_tools` is the canonical tool system.

## Context

The repository previously carried both `api.tools` and `api.assistant_tools`, which created split ownership, inconsistent imports, and regression risk in the chat tool loop.

## Changes

- Hard cutover to `api.assistant_tools.*` imports.
- Removed `apps/api/src/api/tools` from runtime code paths.
- Updated coverage/tooling references from `src/api/tools` to `src/api/assistant_tools`.
- Added route-level integration coverage for provider tool pipelines.

## Migration Note

Downstream code must import tool contracts/registry/executor from `api.assistant_tools.*` only. Any `api.tools.*` imports are no longer supported.

Tool-enabled orchestration is canonical on `POST /chat/conversations/{conversation_id}/messages`. Legacy `POST /api/chat` remains supported for simple chat but is non-canonical for advanced tool workflows.
