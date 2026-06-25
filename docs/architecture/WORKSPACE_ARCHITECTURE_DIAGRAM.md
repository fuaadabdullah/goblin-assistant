# Goblin Assistant — Workspace Architecture Diagram

## 1. Monorepo Workspace Topology (pnpm Workspace)

```mermaid
graph TB
    subgraph "goblin-assistant (Monorepo Root)"
        direction TB
        ROOT["pnpm-workspace.yaml<br/>Root package.json<br/>Makefile (canonical entrypoints)"]

        subgraph "apps/"
            WEB["@goblin/web<br/>Next.js Frontend (Pages Router)<br/>apps/web"]
            API["@goblin/api<br/>FastAPI Backend (Python)<br/>apps/api"]
        end

        subgraph "packages/"
            SHARED["@goblin/shared<br/>Cross-app contracts & types<br/>packages/shared"]
            UI["@goblin/ui<br/>Shared UI components<br/>packages/ui"]
            CONFIG["@goblin/config<br/>Shared configuration<br/>packages/config"]
            TYPES["@goblin/types<br/>TypeScript type definitions<br/>packages/types"]
            SDK["@goblin/sdk<br/>Generated SDK client (OpenAPI)<br/>packages/sdk"]
        end

        subgraph "infra/"
            DOCKER["docker-compose.yml<br/>Docker Compose orchestration"]
            INFRA_DOCKER["infra/docker-compose.yml<br/>Infrastructure compose overlay"]
            K8S["Kubernetes manifests (via /infra)"]
        end

        subgraph "scripts/"
            DEPLOY["deploy/<br/>Deployment scripts"]
            SETUP["setup/<br/>Setup scripts (Supabase, CI/CD, Secrets, Bitwarden)"]
            SECURITY["security/<br/>Security scanning"]
            ARCH_CHECKS["architecture/<br/>Architecture boundary enforcement"]
            OPS["ops/<br/>Operational scripts"]
        end

        subgraph "tooling/"
            CODEMODS["codemods/<br/>Automated code migrations"]
            GENERATORS["generators/<br/>SDK generation, provider JSON"]
            AUTOMATION["automation/<br/>CI/CD helpers"]
            QUALITY["quality/<br/>Test runners, coverage gates"]
            TESTS["tests/<br/>Test manifests & orchestration"]
        end

        subgraph "Supporting"
            SUPABASE["supabase/<br/>Supabase migrations"]
            CONFIG_DIR["config/<br/>Provider config (TOML/JSON)"]
            DOCS["docs/<br/>Architecture, ADRs, Operations, Runbooks"]
            REPORTS["reports/<br/>Generated reports (security, audit, benchmarks)"]
            DATADOG["datadog/<br/>Datadog monitors & SLO definitions"]
        end
    end

    ROOT --> WEB
    ROOT --> API
    ROOT --> SHARED
    ROOT --> UI
    ROOT --> CONFIG
    ROOT --> TYPES
    ROOT --> SDK

    WEB -.->|"depends on"| SHARED
    WEB -.->|"depends on"| UI
    WEB -.->|"depends on"| CONFIG
    WEB -.->|"depends on"| TYPES
    API -.->|"depends on"| SHARED
    API -.->|"depends on"| SDK
    SDK -.->|"generated from"| API
```

## 2. Application Layer — Frontend + Backend Zoom

```mermaid
graph TB
    subgraph "Frontend (apps/web)"
        PAGES["pages/<br/>App pages (Next.js Pages Router)"]
        FEATURES["src/features/<br/>Feature modules"]
        MIDDLEWARE["middleware.ts<br/>Route guard (cookie-based)"]
        API_PROXY["pages/api/<br/>Next API proxy routes"]
        STORE["src/store/<br/>Auth store (Zustand)"]
        CONTEXTS["src/contexts/<br/>ProviderContext, etc."]
        API_CLIENT["src/api/<br/>apiClient.ts + http-client.ts"]
        UTILS["src/utils/<br/>Session persistence helpers"]
    end

    subgraph "Backend (apps/api/src/api)"
        MAIN["main.py<br/>FastAPI app assembly"]
        ROUTERS["Routers:<br/>/chat /auth /routing /api /parse<br/>/execute /health /search /settings<br/>/sandbox /api/privacy /debug /ops /secrets"]
        SERVICES["Services:<br/>Provider Orchestrator, RAG Engine<br/>Task Queue, Cost Tracker"]
        ADAPTERS["Adapters:<br/>Cloud LLM (OpenAI/Anthropic/Gemini)<br/>Local LLM (Ollama/llama.cpp)<br/>Storage (S3/MinIO/boto3)"]
        DB["Database Layer:<br/>SQLite / PostgreSQL + pgvector<br/>Alembic migrations"]
        CELERY["Celery Workers:<br/>high_priority / default / low_priority<br/>+ Celery Beat scheduler"]
    end

    subgraph "Infrastructure Services (Docker Compose)"
        REDIS["Redis 7<br/>Cache + Celery broker"]
        MINIO["MinIO<br/>S3-compatible object store"]
        FLOWER["Flower<br/>Celery monitoring dashboard"]
        MONITOR["Celery Monitor<br/>Metrics exporter"]
        SANDBOX["Sandbox Worker<br/>Secure code execution (Docker)"]
    end

    USER["End User<br/>(Browser)"]

    USER -->|"HTTPS"| PAGES
    PAGES --> FEATURES
    FEATURES --> API_CLIENT
    API_CLIENT --> API_PROXY
    API_CLIENT -->|"direct (some)"| MAIN
    MIDDLEWARE -.->|"protects"| PAGES
    STORE --> UTILS
    CONTEXTS --> API_CLIENT

    API_PROXY -->|"POST /api/generate<br/>GET /api/models<br/>POST /api/auth/validate"| MAIN
    MAIN --> ROUTERS
    ROUTERS --> SERVICES
    SERVICES --> ADAPTERS
    SERVICES --> DB
    ROUTERS --> CELERY
    CELERY <--> REDIS
    MAIN <--> REDIS
    SANDBOX <--> REDIS
    SANDBOX --> MINIO
    MAIN --> SANDBOX
    FLOWER --> REDIS
    MONITOR --> REDIS
```

## 3. Request Flow — End-to-End

```mermaid
sequenceDiagram
    participant User as User Browser
    participant MW as Next Middleware
    participant FE as Next.js App
    participant NAPI as Next API Proxy
    participant API as FastAPI Backend
    participant Router as Routing Service
    participant Provider as AI Provider
    participant DB as Database
    participant Cache as Redis

    User->>MW: HTTP Request
    MW->>MW: Check cookie session
    alt No valid session
        MW-->>User: Redirect to /auth/login
    else Valid session
        MW->>FE: Allow through
    end

    User->>FE: Interact with UI
    FE->>API: API call via HTTP
    alt Requires proxy
        FE->>NAPI: Request
        NAPI->>API: Forward to backend
    else Direct call
        FE->>API: Direct request
    end

    API->>API: Pre-flight checks (auth, rate limit, CORS)
    API->>Router: Classify & route request
    
    alt Chat/Generate
        Router->>Router: Check cost, latency, capability needs
        Router->>Cache: Check cached results
        Cache-->>Router: Cache hit/miss
        Router->>Provider: Invoke model (cloud or local)
        Provider-->>API: Response
    else Search/RAG
        Router->>DB: Vector search (pgvector)
        DB-->>Router: Retrieved context
        Router->>Provider: Augmented generation
        Provider-->>API: Response
    else Sandbox execution
        Router->>Cache: Enqueue job (Redis)
        Cache->>Cache: RQ Worker picks up job
        Cache-->>API: Poll status
    end

    API-->>FE: Structured response
    FE-->>User: Render UI
```

## 4. Agent Archetype Handoffs & Routing

```mermaid
graph TB
    subgraph "Agent Pool"
        GA["General-Purpose Assistant<br/>Tasks, Scheduling, Light Research"]
        DRA["Deep Research Agent<br/>Lit Reviews, Synthesis, Idea Gen"]
        CA["Code Agent<br/>Implement, Debug, Test, Review"]
        FTA["ForgeTM Analyst<br/>Markets, Portfolio, Earnings, Valuation"]
    end

    subgraph "Routing Policy"
        CLASSIFY["Task Classifier<br/>Type / Sensitivity / Urgency"]
        PRIVACY{"Privacy Required?"}
        COST{"Cost &<br/>Capability<br/>Check"}
        LOCAL["Local Model Only<br/>Ollama / llama.cpp"]
        CHEAP["Low-cost Provider"]
        PREMIUM["High-capability Provider"]
    end

    subgraph "Handoff Logic"
        GA -.->|"source-backed research"| DRA
        GA -.->|"modify code"| CA
        GA -.->|"market/investing"| FTA
        DRA -.->|"scheduling result"| GA
        DRA -.->|"implement findings"| CA
        DRA -.->|"financial data"| FTA
        CA -.->|"follow-up tasks"| GA
        CA -.->|"financial validation"| FTA
        FTA -.->|"planning"| GA
        FTA -.->|"tool implementation"| CA
    end

    INCOMING["Incoming Request"] --> CLASSIFY
    CLASSIFY --> PRIVACY
    PRIVACY -->|"Yes"| LOCAL
    PRIVACY -->|"No"| COST
    COST -->|"Simple"| CHEAP
    COST -->|"Complex"| PREMIUM
    COST -->|"Balanced"| ROUTER["Cost-optimized selection"]
    LOCAL --> TELEMETRY
    CHEAP --> TELEMETRY
    PREMIUM --> TELEMETRY
    ROUTER --> TELEMETRY
    TELEMETRY["Response +<br/>Cost/Latency Telemetry"]
```

## 5. Infrastructure & Deployment Topology

```mermaid
graph TB
    subgraph "Deployment Targets"
        CLOUD["Cloud Deployment<br/>Traditional (Kamatera / Render / Fly.io)"]
        K8S_DEPLOY["Kubernetes Deployment<br/>GKE / EKS / AKS"]
        LOCAL_DEPLOY["Local Development<br/>Docker Compose"]
    end

    subgraph "Core Stack"
        API_SVC["FastAPI Backend<br/>:8001"]
        WEB_SVC["Next.js Frontend<br/>:3000"]
        REDIS_SVC["Redis 7<br/>:6379"]
        MINIO_SVC["MinIO S3<br/>:9000 (API) :9001 (Console)"]
    end

    subgraph "Background Workers"
        CELERY_HIGH["Celery Worker - High<br/>concurrency=2"]
        CELERY_DEFAULT["Celery Worker - Default<br/>concurrency=4"]
        CELERY_LOW["Celery Worker - Low<br/>concurrency=2"]
        CELERY_BEAT["Celery Beat Scheduler"]
        SANDBOX_WORKER["Sandbox Worker<br/>Docker-in-Docker"]
    end

    subgraph "Monitoring"
        PROMETHEUS["Prometheus<br/>Metrics & Alerting"]
        FLOWER_SVC["Flower<br/>Celery Dashboard :5555"]
        CELERY_MON["Celery Monitor<br/>:5556"]
        DATADOG_SVC["Datadog<br/>SLOs & Monitors"]
    end

    subgraph "External Integrations"
        AI_PROVIDERS["AI Providers<br/>OpenAI / Anthropic / Gemini / Ollama"]
        SUPABASE_SVC["Supabase<br/>Auth & Storage"]
        EXTERNAL_S3["External S3-compatible<br/>Object Storage"]
    end

    CLOUD --> API_SVC
    CLOUD --> WEB_SVC
    K8S_DEPLOY --> API_SVC
    K8S_DEPLOY --> WEB_SVC
    LOCAL_DEPLOY --> API_SVC
    LOCAL_DEPLOY --> WEB_SVC

    API_SVC --> REDIS_SVC
    API_SVC --> MINIO_SVC
    WEB_SVC --> API_SVC

    CELERY_HIGH --> REDIS_SVC
    CELERY_DEFAULT --> REDIS_SVC
    CELERY_LOW --> REDIS_SVC
    CELERY_BEAT --> REDIS_SVC
    SANDBOX_WORKER --> REDIS_SVC
    SANDBOX_WORKER --> MINIO_SVC

    API_SVC --> CELERY_HIGH
    API_SVC --> CELERY_DEFAULT
    API_SVC --> CELERY_LOW
    API_SVC --> SANDBOX_WORKER

    FLOWER_SVC --> REDIS_SVC
    CELERY_MON --> REDIS_SVC
    PROMETHEUS --> API_SVC
    PROMETHEUS --> REDIS_SVC
    DATADOG_SVC -.->|"logs/metrics"| API_SVC

    API_SVC --> AI_PROVIDERS
    API_SVC --> SUPABASE_SVC
    MINIO_SVC --> EXTERNAL_S3
```

## 6. CI/CD Pipeline

```mermaid
graph LR
    subgraph "CI (GitHub Actions)"
        CHECKOUT["Checkout"]
        INSTALL["Install Dependencies<br/>pnpm install + pip install"]
        LINT["Lint & Format Check<br/>pnpm lint + Ruff + policy_guard"]
        TYPE_CHECK["Type Check<br/>TypeScript + mypy + pyright"]
        TEST["Test Suite<br/>Unit / Integration / Contract / E2E"]
        BUILD["Build<br/>Next.js build + SDK generation"]
        BOUNDARY["Boundary Checks<br/>Architecture + Capability + Cycles"]
        SECURITY["Security Scan<br/>Secret scan + Dependency audit"]
    end

    subgraph "CD (Deployment)"
        DEPLOY_PREVIEW["Deploy Preview<br/>Vercel (frontend)"]
        DEPLOY_STAGING["Deploy Staging<br/>Docker Compose / K8s"]
        DEPLOY_PROD["Deploy Production<br/>Docker Compose / K8s"]
        HEALTH_CHECK["Health Check<br/>curl /health"]
        SMOKE_TEST["Smoke Tests<br/>E2E against deployed target"]
    end

    CHECKOUT --> INSTALL
    INSTALL --> LINT
    INSTALL --> TYPE_CHECK
    LINT --> TEST
    TYPE_CHECK --> TEST
    TEST --> BUILD
    TEST --> BOUNDARY
    BUILD --> SECURITY
    BOUNDARY --> SECURITY

    SECURITY --> DEPLOY_PREVIEW
    SECURITY --> DEPLOY_STAGING
    DEPLOY_STAGING --> HEALTH_CHECK
    HEALTH_CHECK --> SMOKE_TEST
    SMOKE_TEST --> DEPLOY_PROD
```

## 7. Data & Storage Architecture

```mermaid
graph TB
    subgraph "Primary Storage"
        PG[("PostgreSQL / SQLite<br/>Persistent Data<br/>Users, Conversations, Settings")]
        REDIS_DATA[("Redis<br/>Cache, Sessions, Job Queue<br/>Pub/Sub")]
        MINIO_DATA[("MinIO / S3<br/>Artifacts, Sandbox Output<br/>File Storage")]
    end

    subgraph "Vector Storage"
        VECTOR_DB[("Vector DB<br/>pgvector / Qdrant / Chroma<br/>Embeddings & Semantic Search")]
    end

    subgraph "Data Flow Patterns"
        API_WRITE["API writes conversation & user data"]
        API_CACHE["API caches provider responses & sessions"]
        API_RAG["RAG pipeline: embed → store → retrieve"]
        SANDBOX_STORE["Sandbox stores execution artifacts"]
    end

    subgraph "Backup & Migration"
        ALEMBIC["Alembic Migrations<br/>apps/api/alembic/"]
        SUPABASE_MIG["Supabase Migrations<br/>supabase/migrations/"]
    end

    API_WRITE --> PG
    API_CACHE --> REDIS_DATA
    API_RAG --> VECTOR_DB
    SANDBOX_STORE --> MINIO_DATA

    ALEMBIC --> PG
    SUPABASE_MIG -.->|"auth/schema"| PG
```

## 8. Security Boundaries

```mermaid
graph TB
    subgraph "Perimeter"
        MIDDLEWARE_GUARD["Next Middleware<br/>Route Protection"]
        JWT_AUTH["JWT Auth<br/>Backend endpoint protection"]
        API_KEY["x-api-key Auth<br/>Sandbox endpoints"]
        RATE_LIMIT["Rate Limiting<br/>10/min · 100/hr (sandbox)"]
    end

    subgraph "Sandbox Isolation"
        DOCKER_ISOLATION["Docker Container Isolation"]
        NETWORK["network_disabled=True<br/>(except finance allowlist)"]
        CAP_DROP["cap_drop: ALL"]
        SECCOMP["Seccomp Profile"]
        RESOURCE_LIMIT["CPU: 0.25 vCPU<br/>Memory: 256 MB<br/>PID limit: 64"]
        FS_ISOLATION["Root FS: read-only<br/>/tmp: tmpfs 64 MB"]
    end

    subgraph "Code Quality Gates"
        POLICY_GUARD["policy_guard.py<br/>Strict enforcement"]
        BOUNDARY_CHECKS["Architecture Boundary Checks<br/>Import restrictions"]
        SECRET_SCAN["Secret Scanning<br/>Pre-commit + CI"]
        DEP_AUDIT["Dependency Audit<br/>pip-audit + npm audit"]
    end

    MIDDLEWARE_GUARD --> JWT_AUTH
    JWT_AUTH --> API_KEY
    API_KEY --> RATE_LIMIT

    RATE_LIMIT --> DOCKER_ISOLATION
    DOCKER_ISOLATION --> NETWORK
    DOCKER_ISOLATION --> CAP_DROP
    DOCKER_ISOLATION --> SECCOMP
    DOCKER_ISOLATION --> RESOURCE_LIMIT
    DOCKER_ISOLATION --> FS_ISOLATION

    POLICY_GUARD --> BOUNDARY_CHECKS
    BOUNDARY_CHECKS --> SECRET_SCAN
    SECRET_SCAN --> DEP_AUDIT
```

## 9. Directory Tree (Canonical Source Map)

```
goblin-assistant/
├── apps/                                 # Application code
│   ├── web/                              # Next.js frontend (TypeScript)
│   │   ├── pages/                        # Pages Router pages
│   │   │   └── api/                      # Next API proxy routes
│   │   ├── src/                          # Source code
│   │   │   ├── api/                      # API client code
│   │   │   ├── contexts/                 # React contexts
│   │   │   ├── features/                 # Feature modules
│   │   │   ├── store/                    # State management
│   │   │   └── utils/                    # Utilities
│   │   ├── e2e/                          # Playwright E2E tests
│   │   ├── tests/                        # Unit/integration tests
│   │   ├── public/                       # Static assets
│   │   └── config/                       # Jest, Playwright config
│   └── api/                              # FastAPI backend (Python)
│       ├── src/api/                      # FastAPI app source
│       │   ├── routers/                  # Route handlers
│       │   ├── services/                 # Business logic
│       │   └── adapters/                 # External integrations
│       ├── alembic/                      # DB migrations
│       ├── scripts/                      # Backend utility scripts
│       └── tests/                        # Pytest suite
├── packages/                             # Shared code
│   ├── shared/                           # Cross-app contracts & types
│   ├── ui/                               # Shared UI components
│   ├── config/                           # Shared configuration
│   ├── types/                            # TypeScript definitions
│   └── sdk/                              # Generated SDK client
├── docker/                               # Dockerfiles
│   └── sandbox/                          # Sandbox container
├── infra/                                # Infrastructure configs
├── scripts/                              # Repository scripts
│   ├── deploy/                           # Deployment automation
│   ├── setup/                            # Environment setup
│   ├── security/                         # Security tooling
│   ├── architecture/                     # Boundary enforcement
│   └── ops/                              # Operational scripts
├── tooling/                              # Development tooling
│   ├── codemods/                         # Automated refactoring
│   ├── generators/                       # Code generation
│   ├── automation/                       # CI helpers
│   └── quality/                          # Quality gates
├── tests/                                # Cross-cutting tests
│   ├── integration/                      # Integration tests
│   ├── contract/                         # Contract tests
│   ├── e2e/                              # E2E tests
│   └── performance/                      # Performance tests
├── docs/                                 # Documentation
│   ├── architecture/                     # Architecture docs
│   ├── adr/                              # Decision records
│   ├── backend/                          # Backend docs
│   ├── frontend/                         # Frontend docs
│   ├── operations/                       # Operational docs
│   ├── runbooks/                         # Incident runbooks
│   ├── security/                         # Security docs
│   └── decisions/                        # Architecture decisions
├── supabase/                             # Supabase migrations
├── config/                               # Provider configs
├── docker-compose.yml                    # Docker orchestration
├── docker-compose.redis.yml              # Redis-only compose
├── render.yaml                           # Render deployment
├── Makefile                              # Canonical entrypoints
├── pnpm-workspace.yaml                   # Workspace definition
└── package.json                          # Root package