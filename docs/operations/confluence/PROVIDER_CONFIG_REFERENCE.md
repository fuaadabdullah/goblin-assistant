# Provider Config Reference

## Canonical repo sources

- `config/providers.toml`
- `docs/operations/PROVIDERS.md`

## Purpose

Explain how provider config is structured and which fields are canonical versus derived.

## Required statements

- Pricing, limits, aliases, and provider metadata are canonical in `config/providers.toml`.
- Confluence is a read/view layer for these values.
- Generated or copied views must not become hand-maintained config.

## Recommended sections

### Root sections

- `visible_providers`
- `[default]`
- `[load_balancing]`
- `[provider_aliases]`
- `[model_aliases]`
- `[model_context_windows]`
- `[providers.*]`

### Provider entry fields

Explain the purpose of common fields:

- `endpoint`, `endpoint_env`, `api_key_env`
- `default_model`, `models`, `capabilities`
- `priority_tier`, `tier`, `local_routing`
- `costs`, `rate_limits`
- `requires_env`, `selectable_requires_env`
- `hidden`, `is_active`

### Derived surfaces

List generated or derived surfaces:

- `config/providers.json`
- frontend provider routing views
- provider summary artifact from `generate-provider-confluence-summary.py`

### Maintenance rules

- Update this page when config structure changes.
- Do not edit pricing or limits here first.
