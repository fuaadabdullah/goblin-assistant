# API Route Inventory

This document summarizes the current backend route surface derived from
`packages/sdk/openapi/openapi.json`.

For the complete, auto-generated listing, use:

- `tooling/generators/api_route_inventory.py`
- `tooling/generators/generate-api-route-inventory.py`
- generated output: `docs/backend/API_ROUTE_INVENTORY.generated.md`

## Snapshot

- **Paths**: 196
- **Operations**: 204
- **Compatibility alias operations** (`/api/v1`): 45

## Largest route groups

| Group | Operations |
| --- | ---: |
| `/api/v1` | 45 |
| `/debug` | 23 |
| `/health` | 15 |
| `/auth` | 13 |
| `/ops` | 13 |
| `/routing` | 12 |
| `/chat` | 11 |
| `/sandbox` | 11 |
| `/write-time` | 8 |
| `/raptor` | 5 |
| `/semantic-chat` | 5 |
| `/api/privacy` | 4 |
| `/search` | 4 |
| `/secrets` | 4 |
| `/settings` | 4 |
| `/api/orchestrate` | 3 |
| `/account` | 2 |
| `/` | 1 |
| `/api-keys` | 1 |
| `/api/chat` | 1 |

## How to refresh

```bash
python3 tooling/generators/generate-api-route-inventory.py
```

## Notes

- `/api/v1` routes are compatibility aliases for frontend and proxy callers
  that still expect versioned paths.
- The inventory groups routes by prefix so frontend contract work can spot
  mismatches quickly.
- Improving FastAPI route summaries and tags will improve the generated route
  inventory automatically.
