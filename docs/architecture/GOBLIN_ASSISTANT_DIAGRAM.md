---
description: "Comprehensive Mermaid diagrams of the Goblin Assistant architecture"
---

# Goblin Assistant — Architecture Diagrams

## 1. System Context (C4 — Level 1)

```mermaid
graph TB
  subgraph "Users"
    U["End User"]
  end

  subgraph "Goblin Assistant System"
    FE["Next.js Frontend<br/>(apps/web)"]
    API["FastAPI Backend<br/>(apps/api)"]
    SHARED["Shared Packages<br/>(packages/*)"]
  end

  subgraph "External Dependencies"
    DB[("Database<br/>SQLite / Postgres")]
    REDIS[("Redis<br/>Cache & Queue")]
    PROVIDERS["AI Providers<br/>OpenAI / Anthropic / Gemini / Ollama / ..."]
    SANDBOX["Secure Code<br/>Execution Sandbox"]
    VOICE["ElevenLabs<br/>Voice/TTS"]
    SEARCH_EXT["Web Search<br/>& Academic DBs"]
  end

  U -->|"HTTPS"| FE
  FE -->|"API calls (Next API proxies)"| API
  FE -->|"Direct API calls"| API
  API -->|"Read/Write"| DB
  API -->|"Cache / Pub-Sub"| REDIS
  API -->|"Model inference"| PROVIDERS
  API -->|"Run untrusted code"| SANDBOX
  API -->|"TTS synthesis"| VOICE
  API -->|"Fetch data"| SEARCH_EXT
  SHARED -.->|"Contracts / Types / SDK"| FE
  SHARED -.->|"Contracts / Types / SDK"| API
```

## 2. Container Diagram — Frontend

```mermaid
graph TB
  subgraph "Next.js Frontend"
    PAGES["Pages<br/>(apps/web/pages)"]
    FEATURES["Feature Modules<br/>(apps/web/src/features/)"]
    API_PROXY["API Proxy Routes<br/>(apps/web/pages/api/)"]
    MIDDLEWARE["Middleware<br/>Route Guard"]
    AUTH_STORE["Auth Store<br/>(store/authStore.ts)"]
    SESSION["Session Persistence<br/>(utils/auth-session.ts)"]
    PROVIDER_CTX["Provider Context<br/>(contexts/ProviderContext.tsx)"]
    API_CLIENT["API Client<br/>(api/apiClient.ts<br/>api/http-client.ts)"]
  end

  PAGES --> FEATURES
  FEATURES --> API_CLIENT
  API_CLIENT --> API_PROXY
  MIDDLEWARE -.->|"Protects routes"| PAGES
  AUTH_STORE --> SESSION
  PROVIDER_CTX --> API_CLIENT
```

## 3. Container Diagram — Backend (FastAPI)

```mermaid
graph TB
  subgraph "FastAPI Application (apps/api/src/api/main.py)"
    GATEWAY["API Gateway<br/>Request Pre-processing<br/>Auth / Rate-limit / CORS"]
    ROUTER_CHAT["/chat<br/>Conversation management"]
    ROUTER_AUTH["/auth<br/>JWT / Passkeys"]
    ROUTER_ROUTING["/routing<br/>Provider dispatch"]
    ROUTER_API["/api<br/>General endpoints"]
    ROUTER_PARSE["/parse<br/>Document parsing"]
    ROUTER_EXECUTE["/execute<br/>Action execution"]
    ROUTER_HEALTH["/health<br/>Health checks"]
    ROUTER_SEARCH["/search<br/>Search & retrieval"]
    ROUTER_SETTINGS["/settings<br/>User config"]
    ROUTER_SANDBOX["/sandbox<br/>Code sandbox"]
    ROUTER_PRIVACY["/api/privacy"]
    ROUTER_DEBUG["/debug"]
    ROUTER_OPS["/ops"]
    ROUTER_SECRETS["/secrets"]
  end

  subgraph "Services Layer"
    ORCHESTRATOR["Provider Orchestrator<br/>Model routing & dispatch"]
    RAG_ENGINE["RAG Engine<br/>Raptor-backed retrieval"]
    VECTOR_DB["Vector DB<br/>pgvector / Qdrant / Chroma"]
    TASK_QUEUE["Task Queue<br/>Redis / Celery"]
    COST_TRACKER["Cost & Latency<br/>Tracker"]
  end

  subgraph "Adapters"
    ADAPTER_CLOUD["Cloud Provider Adapters<br/>OpenAI / Anthropic / Gemini / ..."]
    ADAPTER_LOCAL["Local Model Adapters<br/>Ollama / llama.cpp"]
    ADAPTER_STORAGE["Storage Adapter<br/>Files / S3-compatible"]
  end

  GATEWAY --> ROUTER_CHAT
  GATEWAY --> ROUTER_AUTH
  GATEWAY --> ROUTER_ROUTING
  GATEWAY --> ROUTER_API
  GATEWAY --> ROUTER_PARSE
  GATEWAY --> ROUTER_EXECUTE
  GATEWAY --> ROUTER_HEALTH
  GATEWAY --> ROUTER_SEARCH
  GATEWAY --> ROUTER_SETTINGS
  GATEWAY --> ROUTER_SANDBOX
  GATEWAY --> ROUTER_PRIVACY
  GATEWAY --> ROUTER_DEBUG
  GATEWAY --> ROUTER_OPS
  GATEWAY --> ROUTER_SECRETS

  ROUTER_CHAT --> ORCHESTRATOR
  ROUTER_ROUTING --> ORCHESTRATOR
  ROUTER_API --> ORCHESTRATOR
  ROUTER_SEARCH --> RAG_ENGINE
  ROUTER_SANDBOX --> TASK_QUEUE

  ORCHESTRATOR --> ADAPTER_CLOUD
  ORCHESTRATOR --> ADAPTER_LOCAL
  ORCHESTRATOR --> COST_TRACKER
  RAG_ENGINE --> VECTOR_DB
  RAG_ENGINE --> ADAPTER_STORAGE
```

## 4. Agent Archetypes & Handoffs

```mermaid
graph TB
  subgraph "Agent Archetypes"
    GA["General-Purpose Assistant<br/>Tasks / Scheduling / Light research"]
    DRA["Deep Research Agent<br/>Lit reviews / Synthesis / Idea gen"]
    CA["Code Agent<br/>Implement / Debug / Test / Review"]
    FTA["ForgeTM Analyst<br/>Markets / Portfolio / Earnings / Valuation"]
  end

  subgraph "Handoff Triggers"
    H1["User needs source-backed synthesis"]
    H2["User asks to modify code"]
    H3["Research output needs scheduling"]
    H4["Research produces implementation plan"]
    H5["User asks market/investing questions"]
    H6["Research needs financial data"]
    H7["Code work creates follow-up tasks"]
    H8["Implementation needs external research"]
    H9["Code needs financial-domain validation"]
    H10["Financial analysis needs planning"]
    H11["Market thesis needs broader research"]
    H12["Analyst needs tool implementation"]
  end

  GA -->|"H1"| DRA
  GA -->|"H2"| CA
  GA -->|"H5"| FTA
  DRA -->|"H3"| GA
  DRA -->|"H4|H8"| CA
  DRA -->|"H6|H11"| FTA
  CA -->|"H7"| GA
  CA -->|"H9"| FTA
  FTA -->|"H10"| GA
  FTA -->|"H12"| CA
```

## 5. Request Routing Sequence

```mermaid
sequenceDiagram
  participant User
  participant Frontend
  participant API
  participant Gateway
  participant Router as RoutingService
  participant Provider
  participant Verifier

  User->>Frontend: Send chat message
  Frontend->>API: POST /v1/chat (auth, tokens)
  API->>Gateway: Pre-flight checks (token budget, rate limiting)
  Gateway->>Router: Classify & choose provider (cost, latency, capability)
  Router->>Provider: Invoke provider (local or cloud)
  Provider-->>Verifier: Raw response
  Verifier-->>API: Verified/filtered response
  API-->>Frontend: Return structured message
  Frontend-->>User: Render response
```

## 6. Hybrid Provider Routing Decision

```mermaid
graph LR
  subgraph "Routing Policy"
    DIRECTION{Incoming Request}
    DIRECTION --> CLASSIFY["Classify Task<br/>Type / Sensitivity / Urgency"]
    CLASSIFY --> CHECK_PRIVACY{"Privacy<br/>Required?"}
    CHECK_PRIVACY -->|"Yes"| LOCAL["Local Model Only<br/>Ollama / llama.cpp"]
    CHECK_PRIVACY -->|"No"| CHECK_COST{"Check Cost<br/>& Capability"}
    CHECK_COST -->|"Simple / Cheap"| CHEAP_MODEL["Low-cost Provider<br/>e.g. cheaper cloud tier"]
    CHECK_COST -->|"Complex / Premium"| PREMIUM_MODEL["High-capability Provider<br/>OpenAI / Anthropic / Gemini"]
    CHECK_COST -->|"Balanced"| ROUTER["Cost-optimized selection<br/>based on latency & quality"]
  end

  LOCAL --> RESPONSE
  CHEAP_MODEL --> RESPONSE
  PREMIUM_MODEL --> RESPONSE
  ROUTER --> RESPONSE[("Response +<br/>Cost/Latency Telemetry")]
```

## 7. Data Flow — Full Stack

```mermaid
flowchart TB
  USER(["User Browser"])
  NEXT["Next.js Frontend"]
  MID["Middleware<br/>(Route Guard)"]
  NAPI["Next API Proxy Routes<br/>pages/api/"]
  FAST["FastAPI Backend"]
  AUTH["Auth Service<br/>JWT / Passkeys"]
  REDIS[("Redis<br/>Cache / Session")]
  DB[("Postgres / SQLite<br/>Persistent Storage")]
  VEC[("Vector DB<br/>pgvector / Qdrant")]
  ADAPTERS["Provider Adapters"]
  LLM["AI Models<br/>Cloud + Local"]

  USER -->|"HTTPS"| NEXT
  NEXT -->|"Request"| MID
  MID -->|"Allow / Redirect"| NEXT
  NEXT -->|"API Call"| NAPI
  NAPI -->|"Proxy"| FAST
  NEXT -->|"Direct (some)"| FAST
  FAST --> AUTH
  FAST <--> REDIS
  FAST <--> DB
  FAST <--> VEC
  FAST --> ADAPTERS
  ADAPTERS --> LLM

  subgraph "Observability"
    LOGS["Structured Logs"]
    METRICS["Metrics<br/>(Prometheus)"]
    TRACES["Distributed Traces"]
  end

  FAST -.-> LOGS
  FAST -.-> METRICS
  FAST -.-> TRACES
```

## 8. Deployment Options

```mermaid
graph TB
  subgraph "Deployment Modes"
    CLOUD["Cloud-Hosted<br/>Kamatera / Render / Fly.io"]
    SELF["Self-Hosted<br/>Bare metal / Docker"]
    HYBRID["Hybrid<br/>Per-tenant routing policies"]
  end

  subgraph "Infrastructure Components"
    DOCKER["Docker Compose<br/>API + Redis + DB"]
    REVERSE["Reverse Proxy<br/>Nginx / Caddy"]
    CI["CI/CD<br/>GitHub Actions"]
    MONITOR["Monitoring<br/>Prometheus + Grafana"]
  end

  CLOUD --> DOCKER
  SELF --> DOCKER
  HYBRID --> DOCKER
  DOCKER --> REVERSE
  DOCKER --> CI
  DOCKER --> MONITOR
```

## 9. Sandbox Execution Lifecycle

```mermaid
sequenceDiagram
  participant Client
  participant API as "POST /sandbox/submit"
  participant Redis
  participant RQ as "RQ Worker<br/>(sandbox-jobs)"
  participant Docker as "Docker Container<br/>(goblin-assistant-sandbox)"
  participant S3 as "S3 Artifact Store"

  Client->>API: source, language, timeout
  API->>API: Auth (x-api-key)<br/>Rate limit (10/min · 100/hr)<br/>Validate (language, timeout 1-300s)
  API->>API: Write main.py / main.js<br/>to JOBS_DIR/{job_id}/
  API->>Redis: SET sandbox:job:{job_id}<br/>status=queued, metadata
  API->>RQ: Enqueue run_job(job_id)
  API-->>Client: 202 { job_id }

  loop Poll until terminal state
    Client->>Redis: GET /sandbox/status/{job_id}
    Redis-->>Client: { status, exit_code, error }
  end

  RQ->>Redis: status=running
  RQ->>RQ: Cosign image verify (optional)
  RQ->>Docker: docker run --rm [hardened]<br/>mount job dir → /work
  Docker->>Docker: sandbox_entrypoint.sh<br/>inner timeout (INNER_TIMEOUT default 20s)
  Docker-->>RQ: exit_code, stdout+stderr
  RQ->>RQ: Write stdout.log
  RQ->>Redis: status=finished|failed<br/>exit_code, finished_at
  RQ->>S3: Upload non-log artifacts<br/>(TTL 7 days)
  RQ->>RQ: Emit sandbox.execution.completed
  RQ->>Docker: Force remove container

  Client->>API: GET /sandbox/logs/{job_id}
  API-->>Client: { logs: combined stdout+stderr }
  Client->>API: GET /sandbox/artifacts/{job_id}
  API->>S3: Generate presigned URLs (5 min TTL)
  API-->>Client: [{ name, size, url }]
```

## 10. Sandbox Security Boundary

```mermaid
graph TB
  subgraph "API Layer — Perimeter"
    AUTH["x-api-key Auth"]
    RATE["Rate Limiting<br/>10 req/min · 100 req/hr"]
    VALID["Input Validation<br/>language ∈ {python, javascript}<br/>timeout 1–300 s · source non-empty"]
  end

  subgraph "RQ Worker Layer"
    COSIGN["Image Signature Check<br/>Cosign (optional)"]
    ACCT["Resource Accounting<br/>Prometheus metrics"]
  end

  subgraph "Docker Isolation Layer"
    NET["network_disabled=True"]
    CAP["cap_drop: ALL"]
    PRIV["no-new-privileges"]
    SECCOMP["seccomp profile<br/>/etc/sandbox/seccomp.json (opt)"]
    APPARMOR["AppArmor profile<br/>sandbox-runner (opt)"]
    FS["Root FS: read-only<br/>/tmp: tmpfs 64 MB<br/>/work: job dir bind-mount rw"]
    USER["Non-root user: runner"]
    MEM["Memory: 256 MB"]
    CPU["CPU quota: 0.25 vCPU"]
  end

  subgraph "Process Layer — Innermost"
    TIMEOUT["Inner timeout<br/>timeout(1) in entrypoint"]
    RLIMIT["setrlimit hard limits<br/>CPU 10s · AS 256 MB<br/>fsize 10 MB · pids 64 · fds 64"]
  end

  AUTH --> COSIGN
  RATE --> COSIGN
  VALID --> COSIGN
  COSIGN --> NET
  ACCT --> NET
  NET --> TIMEOUT
  CAP --> TIMEOUT
  PRIV --> TIMEOUT
  SECCOMP --> TIMEOUT
  APPARMOR --> TIMEOUT
  FS --> TIMEOUT
  USER --> TIMEOUT
  MEM --> TIMEOUT
  CPU --> TIMEOUT
  TIMEOUT --> RLIMIT

  NOTE_FIN["Finance exception:<br/>allow_network=True lifts NET block<br/>for FINANCE_NETWORK_ALLOWLIST only"]
  NOTE_DEV["Dev mode (SANDBOX_ENABLED=false):<br/>falls back to direct subprocess —<br/>Docker isolation does NOT apply"]

  NET -.->|"exception"| NOTE_FIN
  Docker -.->|"bypass"| NOTE_DEV
```
