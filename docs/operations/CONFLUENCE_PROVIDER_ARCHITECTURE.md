# Confluence Provider Architecture Workflow

This runbook defines how Goblin Assistant uses Confluence to reduce provider-documentation debt without replacing repo-tracked technical truth.

## Operating model

- `config/providers.toml` remains the canonical source for provider config, pricing, limits, aliases, and routing metadata.
- `apps/api/src/api/providers/README.md` remains the canonical source for provider adapter lifecycle, onboarding rules, and testing expectations.
- Repo docs under `docs/operations/` and `docs/architecture/` remain the canonical source for code-adjacent operational and architectural truth.
- Confluence is the canonical team navigation layer for provider architecture, onboarding, and incident memory.

Use Confluence to make information easier to discover, review, and cross-link with Jira. Do not move config truth, pricing truth, or provider metadata ownership into Confluence.

## Confluence space

Create one Confluence space:

- Space name: `Provider Architecture`
- Space purpose: architecture overview, provider operating notes, onboarding flow, and incident review index

Required starter pages:

- `Provider Architecture Home`
- `Provider System Overview`
- `Provider Config Reference`
- `Provider Developer Guide`
- `Provider Pricing Reference`
- `Provider Incident Index`
- `Provider Incident Review Template`
- provider family pages:
  - `OpenAI`
  - `Anthropic`
  - `Gemini`
  - `Azure OpenAI`
  - `GCP Self-Hosted`
  - `Colab Worker`
  - `Generic Provider`

## Repo to Confluence source map

Use one declared repo source for each Confluence page:

| Confluence page | Canonical repo source |
| --- | --- |
| `Provider System Overview` | `docs/architecture/ARCHITECTURE_OVERVIEW.md` plus provider routing docs |
| `Provider Config Reference` | `config/providers.toml` and `docs/operations/PROVIDERS.md` |
| `Provider Developer Guide` | `apps/api/src/api/providers/README.md` |
| `Provider Pricing Reference` | `config/providers.toml` |
| `Provider Incident Index` | `docs/operations/JIRA_PROVIDER_OPS.md`, this runbook, and relevant provider-family pages |
| provider family pages | `config/providers.toml`, `docs/operations/PROVIDERS.md`, relevant Jira issues |
| `Provider Incident Review Template` | this runbook and `docs/operations/JIRA_PROVIDER_OPS.md` |

Every Confluence page in this space should contain:

- a `Canonical repo source` section
- a `Last reviewed` date
- a named owner

## Partial automation

Allowed in v1:

- embed Jira issue views for provider bugs and provider incidents
- attach or paste diagrams and generated screenshots when helpful
- generate a provider summary artifact from `config/providers.toml` for Confluence reference views

Not allowed in v1:

- Confluence-driven config changes
- Confluence as the source of pricing values
- full page publishing automation
- scripts that write back provider metadata into the repo

Use the lightweight summary generator when a Confluence page needs a machine-readable reference view:

```bash
python tooling/generators/generate-provider-confluence-summary.py
```

Optional file output:

```bash
python tooling/generators/generate-provider-confluence-summary.py \
  --json-path output/provider-confluence-summary.json
```

## Update triggers

Repo docs must be updated when:

- provider config or runtime behavior changes
- routing, health, quota, or circuit-breaker behavior changes
- onboarding steps for a new provider or provider family change

Confluence pages must be updated when:

- a provider change is architecture-significant
- onboarding flow or contributor checklist changes
- a new provider family becomes supported
- a provider outage produces follow-up learning worth preserving
- a provider incident needs a central index entry or postmortem link

## PR and ops checklist

Pull requests that change provider behavior should verify:

- repo docs were updated when config or runtime behavior changed
- Confluence source page was updated when onboarding or architecture guidance changed
- pricing values were not hand-maintained in two places

Provider incident follow-up should verify:

- the Confluence incident index links the Jira incident or post-incident writeup
- Jira incident is linked from the relevant Confluence provider page
- post-incident writeup uses the Confluence incident review template
- action items link back to Jira tickets

## Acceptance criteria

The rollout is complete when:

- each Confluence page has one declared repo source of truth
- `Provider Developer Guide` in Confluence matches `apps/api/src/api/providers/README.md`
- `Provider Config Reference` matches `config/providers.toml` structure and `docs/operations/PROVIDERS.md`
- at least one provider page embeds or links the correct Jira issue view
- the incident review template is usable with a real provider incident
- no pricing value is maintained manually in both Confluence and the repo without an explicit owner
