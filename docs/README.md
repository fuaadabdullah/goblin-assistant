---
title: "README"
description: "Goblin Assistant app documentation index"
---

# Goblin Assistant Docs

This folder contains app-level documentation for the checked-in `goblin-assistant` codebase.

## Canonical Docs

Start with these files when you need an accurate description of the current repo:

- `../README.md`: top-level project summary and local run instructions
- `setup.md`: local environment and development workflow
- `features.md`: capability/status matrix
- `ARCHITECTURE_OVERVIEW.md`: current frontend/backend wiring
- `../api/README.md`: backend entry guide
- `../api/docs/README.md`: backend route inventory

## Scope

The current app is:

- a Next.js Pages Router frontend in `../src`
- a FastAPI backend in `../api`
- a small set of Next API proxy routes in `../src/pages/api`

## Historical Docs

Many other files in this folder document migrations, experiments, or planned architecture. They may still be useful as implementation notes, but they are not guaranteed to match the current code without verification.

When updating docs, prefer fixing the canonical files above first so new readers are not sent through stale architecture or setup paths.
