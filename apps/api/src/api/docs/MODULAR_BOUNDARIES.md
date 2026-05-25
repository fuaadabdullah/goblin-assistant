# API Modular Boundaries Contract

This contract enforces strict layering for `apps/api/src/api`.

## Layer Ownership

- `routes` and `*_router.py` modules: request parsing, auth/dependency wiring, orchestration.
- `services`: business logic and use-case implementation.
- `storage`: database and persistence access only.
- `core`: domain models, shared policies, and stable abstractions.
- `config`: application configuration and environment schema.

Each module should own:

- models
- interfaces
- services
- tests
- config boundaries

## Import Rules

- Routes/controllers must not import `api.storage` directly.
- Services must not import route/controller modules.
- Services must not import `fastapi` or `starlette`.
- New usage of `api.utils` is blocked outside allowlisted modules.
- Circular dependencies across API modules are forbidden.

## Good vs Bad

Bad:

```python
# api/routes/orders_router.py
from api.storage.orders_repo import OrdersRepo
```

Good:

```python
# api/routes/orders_router.py
from api.services.orders_service import OrdersService
```

Bad:

```python
# api/services/orders_service.py
from fastapi import HTTPException
```

Good:

```python
# api/services/orders_service.py
from api.core.errors import DomainError
```

## Enforcement Commands

- `make check-api-boundaries`
- `make check-api-cycles`
- `make type-check-api-mypy`
- `make type-check-api-pyright`

## Contributor Checklist

Before opening a PR that changes API Python code:

- New/changed functions include typed params and return values.
- Request/response/config data models use Pydantic where applicable.
- Route files only orchestrate and call service-layer interfaces.
- DB access lives in `api.storage` and is consumed through services.
- No new imports from `api.utils` unless explicitly allowlisted.
- Boundary, cycle, mypy, and pyright checks pass locally.
