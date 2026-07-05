# API Route Inventory

This doc points to the generated backend route snapshot.

The checked-in source of truth is:

- `packages/sdk/openapi/openapi.json`
- `packages/sdk/openapi/routes.json`
- `docs/backend/API_ROUTE_INVENTORY.generated.md`

Regenerate everything with:

```bash
python3.11 tooling/generators/generate-sdk-client.sh
python3.11 tooling/generators/generate-api-route-inventory.py --check
```

`make sdk-check` runs the generated-artifact drift check from the repo root.
`make contract-checks` extends that by also validating frontend API path usage.

The generated inventory groups public routes by mounted path, highlights the
`/api/v1` compatibility layer, and lists legacy dual mounts such as
`/settings` where they still exist.
