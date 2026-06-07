# Jira Provider Ops Workflow

This runbook defines how Goblin Assistant uses Jira for provider incidents and platform backlog planning.

## Projects

- `PROVOPS`
  - Use for provider outages, circuit-breaker incidents, and provider pricing or billing changes.
  - Recommended issue types: `Incident`, `Provider Change`.
- `PLAT`
  - Use for provider integrations, retry improvements, technical debt, and planned platform work.
  - Recommended issue types: `Tech Debt`, `Feature`, `Bug`.

## Environment variables

Provider incident automation is disabled unless both of these are set:

```bash
JIRA_PROVIDER_OPS_WEBHOOK_URL=https://api-private.atlassian.com/automation/webhooks/jira/a/<workspace-id>/<rule-uuid>
JIRA_PROVIDER_OPS_PROJECT_KEY=PROVOPS
```

Optional:

```bash
JIRA_PROVIDER_OPS_WEBHOOK_SECRET=replace-with-jira-webhook-token
JIRA_ENVIRONMENT=production
BACKEND_URL=https://your-backend.example.com
```

## Automation scope

Automatic Jira incident creation covers provider incidents only:

- provider health transitions to `degraded`, `unhealthy`, or `billing_issue`
- provider circuit-breaker transitions to `soft_open` or `hard_open`

The backend does not auto-create Jira issues for:

- pricing changes discovered from vendor announcements
- new provider integrations
- retry-policy ideas or other backlog work

Those stay manual and should be filed in Jira directly.

## Jira Automation rule

Goblin Assistant currently uses a project-scoped Jira Automation rule in `PROVOPS`.

Jira Cloud team-managed project rules do not reliably continue from an incoming webhook trigger when the webhook provides no issue context, even if the next step is `Create issue`. The current production workaround is:

- create one stable anchor issue in `PROVOPS`
- set the incoming webhook trigger to `Search for issues`
- use JQL that always resolves to that anchor issue
- let the rule create a fresh incident issue in `PROVOPS`

Current production anchor issue:

- `PROVOPS-1`
- Summary: `Automation Anchor - Provider webhook context`

In Jira Cloud Automation for `PROVOPS`:

1. Create an `Incoming webhook` trigger.
2. If you configured `JIRA_PROVIDER_OPS_WEBHOOK_SECRET`, use the same token in Jira.
3. Set the trigger to `Search for issues`.
4. Use JQL `key = PROVOPS-1` or the key of your own anchor issue.
5. Use `{{webhookData.*}}` smart values from the incoming payload.
6. Deduplicate on `{{webhookData.dedupe_key}}`.
7. Create issues with labels for provider, environment, and backend origin.

This anchor-based setup is a Jira-side workaround, not part of the backend payload contract. If the anchor issue changes, update the trigger JQL and keep the runbook in sync.

Suggested field mapping:

- Project: fixed to `PROVOPS`
- Issue type: `Task` in the live team-managed project configuration
- Summary: `[Provider Incident] {{webhookData.provider_id}} {{webhookData.event_type}}`
- Description: include `{{webhookData.status}}`, `{{webhookData.circuit_state}}`, `{{webhookData.last_error}}`, `{{webhookData.ops_url}}`
- Labels:
  - `provider-{{webhookData.provider_id}}`
  - `env-{{webhookData.environment}}`
  - `incident-source-backend`

Payload fields sent by the backend:

- `event_type`
- `provider_id`
- `status`
- `circuit_state`
- `healthy`
- `configured`
- `avg_latency_ms`
- `consecutive_failures`
- `last_error`
- `occurred_at`
- `environment`
- `service`
- `project_key`
- `dedupe_key`
- `ops_url`

## Manual ticket rules

File a manual `PROVOPS` issue when:

- a provider changed pricing or billing terms
- a provider was added, removed, or deprecated operationally
- the backend did not emit automation because the event came from external discovery rather than runtime behavior

File a `PLAT` issue when:

- adding a provider such as Mistral
- improving Colab Worker retry logic
- fixing routing debt, quota handling, or operational tooling

## Backlog and release cadence

- Review `PROVOPS` incidents as they happen.
- Triage `PLAT` backlog on a regular sprint cadence.
- For releases, assign completed `PLAT` issues to a Jira version and generate Jira release notes first.
- Update [`CHANGELOG.md`](../../CHANGELOG.md) with a short curated summary from that Jira version instead of reconstructing notes from memory.
- After a provider incident with lasting operational or architectural learning, link the Jira issue from the relevant Confluence provider page or incident review page.

## Smoke test

Use this to verify the Jira incoming webhook after configuration:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Automation-Webhook-Token: ${JIRA_PROVIDER_OPS_WEBHOOK_SECRET}" \
  -d '{
    "event_type": "provider.health.updated",
    "provider_id": "openai",
    "status": "unhealthy",
    "circuit_state": "",
    "healthy": false,
    "configured": true,
    "avg_latency_ms": 1250.0,
    "consecutive_failures": 3,
    "last_error": "timeout",
    "occurred_at": "2026-06-05T12:00:00+00:00",
    "environment": "production",
    "service": "goblin-assistant",
    "project_key": "PROVOPS",
    "dedupe_key": "production:provider.health.updated:openai:unhealthy",
    "ops_url": "https://your-backend.example.com/admin/providers/state"
  }' \
  "$JIRA_PROVIDER_OPS_WEBHOOK_URL"
```

Expected result in the current Jira setup:

- the webhook returns `200`
- Jira creates a new `PROVOPS` issue
- labels include `incident-source-backend`, `env-<environment>`, and `provider-<provider_id>`
