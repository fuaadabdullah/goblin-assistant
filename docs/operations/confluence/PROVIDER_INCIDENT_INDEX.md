# Provider Incident Index

## Purpose

Use this page as the landing page for provider incidents, post-incident reviews, and follow-up links.

It should help operators answer:

- what incidents have happened recently
- which provider family pages have active incident context
- whether a post-incident writeup exists
- which Jira follow-up items are still open

## Canonical repo sources

- `docs/operations/JIRA_PROVIDER_OPS.md`
- `docs/operations/CONFLUENCE_PROVIDER_ARCHITECTURE.md`
- relevant provider-family pages in this directory

## Required sections

- `Recent incidents`
- `Post-incident reviews`
- `Follow-up backlog`
- `Provider-family links`

## Content rules

- Treat Jira as the canonical incident system of record.
- Treat Confluence as the canonical team-facing incident memory index.
- Link to Jira issues and Confluence review pages instead of copying long incident logs into multiple places.
- When a provider incident produces durable learning, add or update the relevant provider-family page and link the review from this index.

## Suggested structure

### Recent incidents

- recent `PROVOPS` issues
- links to the affected provider-family pages

### Post-incident reviews

- links to review pages created from `Provider Incident Review Template`
- status for each review: draft, published, or follow-up pending

### Follow-up backlog

- `PLAT` reliability items created from incidents
- any `PROVOPS` incident still awaiting operator follow-up

### Provider-family links

- `OpenAI`
- `Anthropic`
- `Gemini`
- `Azure OpenAI`
- `GCP Self-Hosted`
- `Colab Worker`
- `Generic Provider`
