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

`POST /api/v1/nodes/heartbeat`

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

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/nodes/heartbeat` | Node self-announcement |
| `GET /api/v1/nodes` | All nodes, with effective status and eligibility |
| `GET /api/v1/nodes/{id}` | One node |
| `DELETE /api/v1/nodes/{id}` | Evict immediately, without waiting for expiry |

## Eligibility

A node receives work only when **all** of these hold:

1. Heartbeat is fresher than `GOBLIN_NODE_HEARTBEAT_TTL` (90s).
2. Reported status is `online` — never `degraded` or `offline`.
3. `active_jobs < max_concurrency`.
4. The requested model appears in `models`.
5. Fewer than `GOBLIN_NODE_MAX_FAILURES` consecutive dispatch failures.

A stale heartbeat means **offline regardless of what the node last claimed** —
silence is the only signal we get when a machine is unplugged. Timestamps are
monotonic, not wall clock: staleness is a duration, and a clock adjustment
must never make a live node look dead or a dead one look fresh.

Rule 5 exists so one broken node doesn't make every request for the next 90
seconds pay a timeout before falling through.

## Fallback

Every negative case returns `None`, which the router reads as "use the cloud":
no eligible node, unsupported model, saturation, timeout, connection refused,
TLS failure, a `503` from the node's own concurrency gate, a node with no
advertised endpoint, or an outright bug in the local tier (it is wrapped in a
`try/except` — a defect here degrades to cloud rather than 500-ing the user).

Streaming skips the local tier entirely: the node agent forces `stream:false`.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `GOBLIN_LOCAL_NODES_ENABLED` | `true` | `false` restores exact pre-existing routing |
| `GOBLIN_NODE_HEARTBEAT_TTL` | `90` | Tolerates two dropped 30s beats |
| `GOBLIN_NODE_TIMEOUT` | `60` | Wait before giving up on a node |
| `GOBLIN_NODE_MAX_FAILURES` | `3` | Consecutive failures before shedding |
| `GOBLIN_NODE_DEFAULT_MODEL` | `llama3.1:8b` | Used when the caller names none |
| `GOBLIN_NODE_CLIENT_CERT/KEY`, `GOBLIN_NODE_CA_CERT` | — | mTLS identity presented to nodes |

Without a client certificate signed by the node fleet CA, the node drops the
API at the TLS handshake. That is the intended behaviour, not a misconfiguration.

## Known limitation: multi-worker deployments

The registry is in-memory. Nodes re-announce every ~30s, so an API restart
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

## Not implemented

- **Streaming** to local nodes.
- **Multi-node scheduling.** `eligible_nodes()` sorts by `active_jobs` then
  `node_id`. Real scheduling — VRAM fit, model residency, locality — is a
  separate problem that should not be half-solved here.
- Persistence of the registry (see the multi-worker limitation above).
