# Local compute nodes

Goblin can serve inference from machines we own before reaching for a cloud
provider. This describes the API side; the node side lives in
[`goblin-node-agent`](https://github.com/fuaadabdullah/goblin-node-agent).

## Why this is a tier, not a provider

```
HybridRouter
├── Local Compute
│   └── NodeRegistry
│       └── node-001  (RTX 3060, llama3.1:8b)
└── Cloud Providers
    ├── Groq
    ├── DeepSeek
    └── Gemini …
```

Providers are interchangeable vendor endpoints, ranked against each other on
cost and latency. Nodes are machines we own, with **capacity**, **model
residency** and **health** — none of which the provider abstraction can
express. Registering `node-001…node-N` as pseudo-providers would put entries
with no meaningful price into every cost calculation and ranking decision in
the router, and would get worse with each machine added.

So `route_task` consults the local tier first and, on any negative result,
proceeds down the completely untouched cloud ladder.

## Heartbeat contract

Nodes announce themselves; they are not discovered. A node is the only party
that knows whether its GPU is healthy, which models are resident, and how much
of its concurrency budget is spent.

`POST /api/v1/nodes/heartbeat` — **authenticated**:

```http
Authorization: Bearer <GOBLIN_NODE_REGISTRATION_SECRET>
```

```json
{
  "node_id": "node-001",
  "node_type": "inference",
  "status": "online",
  "backend": "ollama",
  "gpu": "RTX 3060 12GB",
  "models": ["llama3.1:8b"],
  "active_jobs": 0,
  "max_concurrency": 1,
  "endpoint": "https://node-001.tailnet:8090"
}
```

Upserts by `node_id` — the first heartbeat registers, later ones refresh. A
node that restarts or changes its model set needs no operator action.

| Endpoint | Auth | Purpose |
| --- | --- | --- |
| `POST /api/v1/nodes/heartbeat` | Node secret | Node self-announcement |
| `GET /api/v1/nodes` | Operator secret | All nodes, status and eligibility |
| `GET /api/v1/nodes/{id}` | Operator secret | One node |
| `DELETE /api/v1/nodes/{id}` | Operator secret | Evict without waiting for expiry |

## Security

The control plane is authenticated because it is not merely status metadata.
`endpoint` decides where dispatch sends **real user prompts**, under the API's
own TLS identity — an unauthenticated heartbeat is a prompt-exfiltration and
SSRF primitive, not a cosmetic concern.

Three controls, in order of importance:

1. **Heartbeat authentication.** A shared bearer secret, compared in constant
   time. **Fails closed**: with `GOBLIN_NODE_REGISTRATION_SECRET` unset the
   endpoint returns 503 and registers nothing. Nodes are not users, so this
   deliberately avoids the session/database path on every beat.
2. **Endpoint policy.** Advertised endpoints must be well-formed `http(s)`
   with no credentials, query or fragment; plaintext `http` is permitted only
   to loopback. Validated at registration *and* re-validated at dispatch, so
   tightening policy also constrains nodes already resident in the registry.
3. **Host allowlist.** `GOBLIN_NODE_ENDPOINT_ALLOWLIST` is what turns a leaked
   registration secret from "attacker receives your users' prompts" into
   "attacker achieves nothing". **Set it in production.** Without it, an
   authenticated caller may advertise any structurally valid host — there is a
   test that documents exactly this residual risk.

### Authentication is not authorization

Management routes use a **separate** `GOBLIN_NODE_OPERATOR_SECRET`, not
`get_current_user`. Goblin has no role model — `UserModel` carries no admin or
superuser column — so "authenticated" would have meant *any* user of a
multi-user deployment could enumerate the fleet or `DELETE` node-001.

The two secrets are deliberately distinct, and the code **refuses to start
serving management routes if they are equal**. The registration secret is
copied onto every node in the fleet; if it also opened management,
compromising any single node would hand over the ability to evict all the
others. Both fail closed when unset.

Replace this with a real authorization dependency once roles exist — the
secret is a stand-in for RBAC that does not yet exist, not a preferred design.

### Future hardening

Per-node secrets rather than one shared value, HMAC-signed timestamped
heartbeats to stop replay, or API-side mTLS. Not needed while the fleet is one
machine, but the shared secret is the first thing to outgrow.

## Eligibility

A node receives work only when **all** of these hold:

1. Heartbeat is fresher than `GOBLIN_NODE_HEARTBEAT_TTL` (90s).
2. Reported status is `online` — never `degraded` or `offline`.
3. Reported capacity has room **and** this API process can atomically reserve a local dispatch slot.
4. The requested model appears in `models`.
5. The node's failure breaker is closed (see below).

A stale heartbeat means **offline regardless of what the node last claimed** —
silence is the only signal we get when a machine is unplugged. Timestamps are
monotonic, not wall clock: staleness is a duration, and a clock adjustment
must never make a live node look dead or a dead one look fresh.

Rule 5 exists so one broken node doesn't make every request for the next 90
seconds pay a timeout before falling through. After
`GOBLIN_NODE_MAX_FAILURES` consecutive dispatch failures the node is shed for
`GOBLIN_NODE_FAILURE_COOLDOWN` seconds, then goes half-open: the next dispatch
is a probe, success closes the breaker and failure re-arms the cooldown.
**Heartbeats do not reset it** — a heartbeat proves the control plane is up,
not that inference, TLS, or the advertised model works.

### Capacity accounting

Effective load is `max(active_jobs + reservations made since that heartbeat,
reservations held by this process)`. A heartbeat already counts any of our jobs
that were in flight when it was sent, so only newer reservations are added on
top; our own in-flight count is a floor in case the node has since finished
other callers' work and under-reports.

## Fallback and failure semantics

Every eligible node is tried in load order. Only when all of them miss does the
local tier return `None`, which the router reads as "use the cloud": no
eligible node, unsupported model, saturation, timeout, connection refused, TLS
failure, a node with no advertised endpoint, or an outright bug in the local
tier (it is wrapped in a `try/except` — a defect here degrades to cloud rather
than 500-ing the user).

Not every miss is a health signal. Only these feed the failure breaker:

| Outcome | Falls back | Counts as node failure |
| --- | --- | --- |
| Connect/read timeout, refused, TLS error, 5xx, 401/403 | yes | **yes** |
| `503` / `429` (the agent's own concurrency gate) | yes | no — flow control |
| Request-scoped 4xx (400, 404, 405, 409, 413, 415, 422) | yes | no — says nothing about the node |
| Stream fails **after** the first token | **no** — surfaces as an interrupted stream | **yes** |

A broken or unreadable mTLS certificate is re-attempted on every call (the SSL
context is cached only after it builds successfully), so the tier keeps
failing closed rather than silently falling back to system trust.

## Cost

Local responses report `cost_usd: 0.0` with real token counts from the node in
the same `usage` shape cloud providers use (`prompt_tokens`,
`completion_tokens`, `total_tokens`), at the top level and under `result`.

## Streaming

With `GOBLIN_NODE_STREAMING_ENABLED=true`, `route_task(..., stream=True)`
tries the local tier through the agent's `POST /inference/stream` (NDJSON).
The stream counts as served only once the **first token** arrives, so a node
that dies before speaking falls back to the next node or the cloud invisibly.
After the first token there is no silent fallback — splicing a cloud answer
onto half a local one is worse than an honest interruption — so the stream
raises `NodeStreamInterruptedError` and the node takes a breaker failure.

Chunks match the cloud providers' `{"text": ...}` shape; the final chunk is
`{"text": "", "done": true, "usage": {...}, "cost_usd": 0.0}`, which existing
consumers skip as empty text. The node's reservation is held until the stream
is exhausted, fails, or is closed — including a stream closed before it was
ever read. Agents without the stream endpoint answer 404, which falls back
without tripping the breaker; keep the flag off until the fleet is upgraded.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `GOBLIN_LOCAL_NODES_ENABLED` | **`false`** | Ships off; production opts in |
| `GOBLIN_NODE_REGISTRATION_SECRET` | — | **Required.** Unset = heartbeats refused |
| `GOBLIN_NODE_OPERATOR_SECRET` | — | **Required** for management routes. Must differ from the above |
| `GOBLIN_NODE_ENDPOINT_ALLOWLIST` | — | Permitted endpoint hosts. Set in production |
| `GOBLIN_NODE_HEARTBEAT_TTL` | `90` | Tolerates two dropped 30s beats |
| `GOBLIN_NODE_CONNECT_TIMEOUT` | `3` | Cap on discovering a node is absent |
| `GOBLIN_NODE_TIMEOUT` | `300` | Read timeout — generation may be slow |
| `GOBLIN_NODE_WRITE_TIMEOUT` | `10` | Request write timeout |
| `GOBLIN_NODE_ALLOW_INSECURE_ENDPOINTS` | `false` | Development only; permits non-loopback HTTP |
| `GOBLIN_NODE_MAX_FAILURES` | `3` | Consecutive failures before shedding |
| `GOBLIN_NODE_FAILURE_COOLDOWN` | `60` | Seconds shed before a half-open probe |
| `GOBLIN_NODE_STREAMING_ENABLED` | `false` | Serve `stream=True` locally; needs agent `/inference/stream` |
| `GOBLIN_NODE_DEFAULT_MODEL` | `llama3.1:8b` | Used when the caller names none |
| `GOBLIN_NODE_CLIENT_CERT/KEY`, `GOBLIN_NODE_CA_CERT` | — | mTLS identity presented to nodes |

Without a client certificate signed by the node fleet CA, the node drops the
API at the TLS handshake. That is the intended behaviour, not a misconfiguration.

## Timeout policy

Connect and read budgets are separate, because the two failures are nothing
alike:

| Failure | Behaviour | Budget |
| --- | --- | --- |
| Process killed | RST, refused immediately | ~0 s |
| Tunnel/firewall blackhole | SYN goes nowhere | `GOBLIN_NODE_CONNECT_TIMEOUT` (3 s) |
| Node generating a long answer | Legitimately slow | `GOBLIN_NODE_TIMEOUT` (300 s) |

A single shared budget would let a blackholed node stall the user for the
whole timeout before the cloud is tried — precisely the "local-first made
Goblin slow" failure this tier must never cause. A 3060 taking a while over a
long answer is fine; taking 60 seconds to discover the computer isn't there
is not.

## Known limitation: multi-worker deployments

The registry is in-memory. API-side reservations are counted on top of reported `active_jobs` (see *Capacity accounting*), preventing concurrent requests in the **same API process** from oversubscribing the node between heartbeats. Nodes re-announce every ~30s, so an API restart
costs at most one heartbeat interval of blindness — cheaper than the
consistency problems of persisting state that is stale the moment it is written.

**However**, with multiple API workers each keeps its own view. A node
heartbeats to whichever worker the load balancer picks, so another worker may
not know about it. The worst case is a request going to the cloud that could
have gone local — acceptable while local compute is an optimisation with a
cloud fallback. This must move to Redis or the database **before** local nodes
ever become the only path.

## Acceptance test

Verified against real hardware on 2026-08-19:

1. Node agent heartbeats in → registry shows `online`, `eligible: true`.
2. `"Explain compound interest"` → served by `local:node-001` over mTLS,
   **64.1 tok/s** on the RTX 3060.
3. Node process killed → same prompt returns `None` in **0.00s** (connection
   refused is immediate), router proceeds to the cloud ladder.
4. Heartbeat aged past TTL → status becomes `offline`.

Re-verified with heartbeat authentication and a host allowlist enforced:
65.4 tok/s, same fallback behaviour. A blackholed host (RFC 5737 TEST-NET-2,
which drops rather than refuses) falls back inside the connect budget — this
is covered by an automated test, not just the manual run.

## Not implemented

- Per-node secrets, HMAC-signed heartbeats, replay protection.
- **Role-based authorization.** The operator secret is a stand-in until
  `UserModel` grows a role and a real `require_admin` dependency exists.
- **Multi-node scheduling.** `eligible_nodes()` sorts by `active_jobs` then
  `node_id`. Real scheduling — VRAM fit, model residency, locality — is a
  separate problem that should not be half-solved here.
- Persistence of the registry (see the multi-worker limitation above).
