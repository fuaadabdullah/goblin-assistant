# Dispatcher Decomposition

## Status
accepted

## Context
The provider dispatcher became a large orchestration surface that mixed catalog loading, discovery, routing, execution, warmup, debug reporting, and secret sanitization. That size made it difficult to reason about provider behavior and increased the risk of breaking compatibility seams during refactors.

## Decision
Keep `apps/api/src/api/providers/dispatcher.py` as the stable public dispatcher facade, while moving implementation details into `apps/api/src/api/providers/dispatcher_pkg/`.

The dispatcher package owns the split responsibilities:
- `catalog.py` for canonical provider IDs and catalog refresh;
- `config.py` for provider TOML loading and alias normalization;
- `discovery.py` for provider lookup and inventory building;
- `execution.py` for dispatch and stream wrapping;
- `routing.py` for ranking and selection helpers;
- `lifecycle.py` for preflight, restore, and warmup orchestration;
- `sanitization.py` for structured secret redaction;
- `test_mode.py` for deterministic failure and delay hooks;
- `debug.py` for inventory and health reporting.

## Consequences
- The root dispatcher keeps the historical import and monkeypatch surface intact.
- Implementation concerns are isolated into smaller modules with narrower responsibilities.
- Provider routing and execution changes can be tested independently from catalog and debug behavior.

## Operational Notes
- The canonical package for provider-dispatch logic is `api.providers.dispatcher_pkg`.
- Tests that need compatibility seams should continue to patch `api.providers.dispatcher` unless they are explicitly targeting a package module.
- New dispatcher behavior should default to the package modules first and only expose facade methods in the root module when compatibility requires it.
