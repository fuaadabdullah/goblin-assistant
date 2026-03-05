---
description: 'Core Identity and positioning for GoblinOS Assistant — hybrid, multi-provider AI orchestration'
---

# GoblinOS Assistant — Core Identity

GoblinOS Assistant is a multi-provider, hybrid local/cloud AI assistant platform built for privacy, cost-efficiency, and extensibility. It’s not a simple “ChatGPT wrapper”—it’s an orchestration layer that intelligently routes each request across cloud providers and local models based on cost, latency, and capability.

## 1. What GoblinOS Provides

- Choice — Use multiple AI providers and local models through a unified API and adapter system.

- Control — Decide which workloads run locally vs. in the cloud and define routing policies.

- Cost-efficiency — Route workloads to the cheapest viable option while preserving quality.

- Extensibility — Plug in new providers, tools, and workflows with a standard adapter interface.

## 2. Key Characteristics

### 2.1 Hybrid Architecture

GoblinOS spans both cloud and local environments:

- Cloud Providers: OpenAI, Anthropic, Google Gemini, DeepSeek, Grok, Moonshot, SiliconFlow, and more via plugin adapters.
- Local Models: llama.cpp, Ollama, and custom local LLM proxies.
- Intelligent Routing: Requests are dispatched based on cost (price per token/call), latency, and capability (model quality and context length). GoblinOS can route lightweight tasks to cheap/local models, heavy reasoning tasks to premium cloud models, and sensitive data to strictly local execution.

### 2.2 Privacy-First Design

GoblinOS is designed for users who want data control and privacy:

- Local Execution Option: Run prompts, RAG, and tools entirely on local models for sensitive workloads.
- End-to-End Encryption: Conversation data is encrypted in transit and optionally at rest.
- Self-Hostable: Deploy to Kamatera, Fly.io, bare metal, or a private cloud.

### 2.3 Enterprise-Grade Features

- Multi-Tenancy with isolated data and permissions.

- API Key Management with secure rotation and scoping.

- Usage Analytics & Cost Tracking (per-user / team reports, provider cost breakdowns).

- Audit Logging: Who called what, which provider/model was used, and when.

### 2.4 Advanced Capabilities

- RAG Engine (Raptor-backed) for retrieval and reasoning over long context.

- Vector DB-backed retrieval (pluggable backends like pgvector, Qdrant, Chroma).

- Secure Code Execution sandbox for safe code running.

- Integrated Web Search and File Processing pipelines (PDF/docs parsing).

- ElevenLabs (or equivalent) voice/TTS integrations.

- RAG Engine (Raptor-backed) for retrieval and reasoning over long context.

- Vector DB-backed retrieval (pluggable backends like pgvector, Qdrant, Chroma).

- Secure Code Execution sandbox for safe code running.

- Integrated Web Search and File Processing pipelines (PDF/docs parsing).

- ElevenLabs (or equivalent) voice/TTS integrations.
- RAG Engine (Raptor-backed) for retrieval and reasoning over long context.
- Vector DB-backed retrieval (pluggable backends like pgvector, Qdrant, Chroma).
- Secure Code Execution sandbox for safe code running.
- Integrated Web Search and File Processing pipelines (PDF/docs parsing).
- ElevenLabs (or equivalent) voice/TTS integrations.

## 3. High-Level Architecture (Short)

At a high-level GoblinOS is structured as:

- User Interface (Web/Mobile) ↔ API Gateway (FastAPI) ↔ Provider Orchestrator

- Authentication (JWT/Passkeys) and Local LLM Proxy (llama.cpp/Ollama)

- RAG Engine (Vector DB) and Task Queue (Celery/Redis)

Key pieces: provider orchestration, routing, RAG indexing and retrieval, and background task processing.

## 4. Unique Differentiators

- Cost Optimization: Dynamic model switching by price, latency, and task category.

- Fault Tolerance: Circuit breakers and provider bulkheads for resiliency.

- Plugin System: Easy to add providers, tools, and workflows.

- Observability: Rich metrics and logs per provider/model, detailed cost and latency tracking.

## 5. Target Users

- Developers who want programmable AI backends with tools like code execution and RAG.

- Enterprises that require provider redundancy, auditability, and data segregation.

- Privacy-Conscious customers who prefer local processing.

- Cost-Conscious teams who want to control and optimize spend.

## 6. Deployment Modes

- Cloud-Hosted, Self-Hosted, or Hybrid — use per-tenant policies to decide how workloads are routed.

## 7. Slogan & Short Pitches

Tagline:

> GoblinOS is a multi-provider, privacy-first AI assistant platform that routes workloads across cloud and local models for maximum control and cost-efficiency.

Short pitch:

> GoblinOS Assistant is a “Swiss Army knife” AI platform that connects to multiple LLM providers and local models, then intelligently routes each request based on cost, latency, and capability. It’s built for developers and teams who care about privacy, auditability, and flexibility, with RAG, code execution, web search, and voice support baked in.

## 8. Next Steps & Where to Learn More

- See `ARCHITECTURE_OVERVIEW.md` for an end-to-end diagram and routing sequence.

- See `backend/docs/` for the canonical backend design, provider adapters, and CI/Deployment guidance.

- If you plan to extend GoblinOS, review `backend/providers/` and `backend/services/routing.py` for implementing new adapters and routing logic.

---
