---
description: 'Sequence diagram for request routing in GoblinOS Assistant'
---

# Request Routing Sequence

This diagram shows the core request routing sequence from the user to the AI provider and back, including gateway checks and verification.

```mermaid
sequenceDiagram
  participant Client
  participant Frontend
  participant API
  participant Gateway
  participant Router as RoutingService
  participant Provider
  participant Verifier

  Client->>Frontend: Send chat message
  Frontend->>API: POST /v1/chat (auth, tokens)
  API->>Gateway: Pre-flight checks (token budget, rate limiting)
  Gateway->>Router: Classify & Choose provider (RAG decision)
  Router->>Provider: Invoke provider (local or cloud)
  Provider-->>Verifier: Response
  Verifier-->>API: Verified/filtered response
  API-->>Frontend: Return message
  Frontend-->>Client: Render response
```

Notes:

- Replace `Provider` in the diagram with `Ollama`, `OpenAI`, `Anthropic`, etc. when you want provider-specific flows.
