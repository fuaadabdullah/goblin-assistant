# Provider System Overview

## Canonical repo sources

- `docs/architecture/ARCHITECTURE_OVERVIEW.md`
- `docs/operations/PROVIDERS.md`
- `config/providers.toml`

## What this page explains

- provider selection and routing
- health, quota, and circuit-breaker concepts
- provider config ownership
- how Jira and Confluence fit into provider operations

## Recommended sections

### Data flow

Describe the path from frontend request to backend routing, provider selection, execution, and provider health updates.

### Routing and failover

Summarize:

- canonical provider ids
- aliases and model aliases
- candidate ordering and failover
- when circuit state affects selectability

### Operational signals

Summarize:

- health transitions
- circuit-breaker transitions
- Jira incident creation
- Confluence post-incident review expectations

### Linked references

- link back to repo diagrams
- embed or link current `PROVOPS` incidents
- link the `Provider Config Reference` and `Provider Developer Guide`
