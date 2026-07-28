# Provider Developer Guide

## Canonical repo source

- `apps/api/src/api/providers/README.md`

## Purpose

Provide an onboarding-friendly view of the provider adapter contract and the minimum checklist for adding or changing a provider.

## Recommended sections

### Before writing code

- confirm canonical provider id
- confirm env var names
- confirm provider family ownership
- confirm required tests and docs

### Adapter checklist

- implement adapter
- register provider
- add TOML config
- verify health behavior
- verify failover behavior
- add focused tests

### Failure-handling rules

- when to return `ProviderResult(ok=False, ...)`
- when to raise
- stream failure expectations
- circuit-breaker implications

### Documentation handoff

- update repo docs if runtime or config behavior changed
- update provider-family Confluence page if onboarding or architecture context changed
- link relevant Jira backlog or incident issues
