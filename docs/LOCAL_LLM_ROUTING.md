---
title: "LOCAL LLM ROUTING"
description: "Local LLM Intelligent Routing Guide"
---

# Local LLM Intelligent Routing Guide

## Overview

This guide describes the intelligent routing system for local LLM models deployed on the Kamatera VPS. The routing logic automatically selects the best model based on request characteristics: **intent**, **context length**, **latency requirements**, and **cost priorities**.

## Available Models

| Model          | Size  | Context Window | Best For                              | Response Time |
| -------------- | ----- | -------------- | ------------------------------------- | ------------- |
| **mistral:7b** | 4.4GB | 8,192 tokens   | High quality, creative, coding, legal | ~14-15s       |
| **qwen2.5:3b** | 1.9GB | 32,768 tokens  | Long documents, RAG, multilingual     | ~14s          |
| **phi3:3.8b**  | 2.2GB | 4,096 tokens   | Low-latency chat, UI responses        | ~10-12s       |
| **gemma:2b**   | 1.7GB | 8,192 tokens   | Ultra-fast, classification, status    | ~5-8s         |

## Routing Rules

### Rule 1: Ultra-Low Latency → gemma:2b

**Conditions:**

- Latency target: `ultra_low` (< 100ms target)
- OR Intent: `classification`, `status`, `microop`
- OR Cost priority enabled AND context < 100 tokens

**Parameters:**

```python
{
    "temperature": 0.0,
    "top_p": 0.9,
    "max_tokens": 40
}
```

**Use Cases:**

- Status checks
- Text classification (spam detection, sentiment analysis)
- Quick yes/no questions
- Pre-filtering before expensive operations

### Rule 2: Long Context / Multilingual / RAG → qwen2.5:3b

**Conditions:**

- Context length > 8,000 tokens
- OR Non-English language detected
- OR Intent: `rag`, `retrieval`, `translation`

**Parameters:**

```python

{
    "temperature": 0.0,  # For RAG/retrieval
    "temperature": 0.3,  # For other tasks
    "top_p": 0.9,
    "max_tokens": 1024
}
```

**Use Cases:**

- Long document summarization
- RAG (Retrieval-Augmented Generation) queries
- Multilingual conversations
- Translation tasks
- Large context window requirements (up to 32K tokens)

### Rule 3: Low-Latency Chat → phi3:3.8b

**Conditions:**

- Latency target: `low` (100-200ms target)
- OR Intent: `chat` AND context < 2,000 tokens

**Parameters:**

```python
{
    "temperature": 0.15,
    "top_p": 0.9,
    "max_tokens": 128
}
```

**Use Cases:**

- Conversational UI
- Multi-turn chat
- Interactive assistants
- Quick Q&A
- Technical support dialogues

### Rule 4: High Quality → mistral:7b

**Conditions:**

- Intent: `summarize`, `explain`, `code-gen`, `creative`, `legal`
- AND Context <= 8,000 tokens

**Parameters:**

```python

{
    "temperature": 0.0,  # For code generation
    "temperature": 0.2,  # For explanations/summaries
    "temperature": 0.6,  # For creative writing
    "top_p": 0.95,
    "max_tokens": 512,
    "stop": ["\n\n"]  # For concise responses
}
```

**Use Cases:**

- Code generation with best practices
- Detailed explanations
- Creative writing
- Legal/compliance content
- High-quality summaries
- Technical documentation

## System Prompts

The routing system automatically selects appropriate system prompts based on intent:

### Default Prompt

```
You are a concise, accurate assistant. Use numbered steps for procedures.
If unsure, say 'I don't know — check sources.'
Do not invent facts; if information depends on external sources label it.
```

### Code Generation Prompt

```
You are a precise coding assistant. Provide clean, working code with brief explanations.
Use best practices and include error handling.
Do not invent facts; if information depends on external sources label it.
```

### Creative Writing Prompt

```
You are a creative and imaginative assistant. Be expressive while remaining helpful.
Do not invent facts; if information depends on external sources label it.
```

### RAG/Retrieval Prompt

```
You are a retrieval assistant. Answer based strictly on provided context.
If the answer is not in the context, say 'This information is not available in the provided context.'
Do not invent facts; cite sources when available.
```

### Classification Prompt

```
You are a classification assistant. Provide only the requested classification without explanation.
Be precise and consistent.
```

## Usage Examples

### Example 1: Code Generation

**Request:**

```python
{
    "messages": [
        {
            "role": "user",
            "content": "Write a Python function to implement binary search"
        }
    ]
}
```

**Routing Decision:**

- Model: `mistral:7b`
- Intent: `code-gen` (detected)
- Temperature: 0.0
- Reasoning: High-quality code generation required

### Example 2: Quick Status Check

**Request:**

```python

{
    "messages": [
        {"role": "user", "content": "What's the deployment status?"}
    ],
    "latency_target": "ultra_low"
}
```

**Routing Decision:**

- Model: `gemma:2b`
- Intent: `status` (detected)
- Temperature: 0.0
- Reasoning: Ultra-low latency requirement + status intent

### Example 3: Long Document RAG

**Request:**

```python
{
    "messages": [
        {
            "role": "user",
            "content": "Based on this document, what are the key findings?"
        }
    ],
    "intent": "rag",
    "context": "<10,000 token document>"
}
```

**Routing Decision:**

- Model: `qwen2.5:3b`
- Intent: `rag` (explicit)
- Temperature: 0.0
- Context: 10,012 tokens
- Reasoning: Long context (>8K) + RAG intent + 32K window support

### Example 4: Conversational Chat

**Request:**

```python

{
    "messages": [
        {"role": "user", "content": "Hi! How are you?"},
        {"role": "assistant", "content": "I'm doing well!"},
        {"role": "user", "content": "Can you help me?"}
    ],
    "latency_target": "low"
}
```

**Routing Decision:**

- Model: `phi3:3.8b`
- Intent: `chat` (detected)
- Temperature: 0.15
- Reasoning: Low-latency conversational flow

## API Integration

### Using the Routing Service

```python
from services.routing import RoutingService

# Initialize service
routing_service = RoutingService(db, encryption_key)

# Route a chat request
result = await routing_service.route_request(
    capability="chat",
    requirements={
        "messages": [
            {"role": "user", "content": "Explain quantum computing"}
        ],
        "latency_target": "medium"
    }
)

# Result includes:
# - selected model
# - recommended parameters
# - system prompt
# - routing explanation
```

### Direct Model Selection

```python

from services.local_llm_routing import select_model, Intent, LatencyTarget

# Select model with explicit intent
model_id, params = select_model(
    messages=[{"role": "user", "content": "Write a function"}],
    intent=Intent.CODE_GEN,
    latency_target=LatencyTarget.MEDIUM
)

# Result:

# model_id = "mistral:7b"

# params = {"temperature": 0.0, "top_p": 0.95, "max_tokens": 512}
```

## Intent Detection

The system automatically detects intent from message content using keyword matching:

| Keywords                   | Intent           |
| -------------------------- | ---------------- |
| summarize, summary, tldr   | `summarize`      |
| explain, what is, how does | `explain`        |
| code, function, implement  | `code-gen`       |
| story, poem, creative      | `creative`       |
| translate, translation     | `translation`    |
| classify, category, label  | `classification` |
| status, health, check      | `status`         |

You can also **explicitly provide intent** to override detection:

```python
{
    "messages": [...],
    "intent": "creative"  # Force creative writing route
}
```

## Performance Optimization Tips

### 1. KV Cache Reuse

For multi-turn conversations, reuse key-value cache to reduce latency:

```python

# First turn
response1 = await ollama_adapter.chat(
    model="phi3:3.8b",
    messages=[{"role": "user", "content": "Hi"}]
)

# Subsequent turns reuse cache
response2 = await ollama_adapter.chat(
    model="phi3:3.8b",
    messages=[
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": response1},
        {"role": "user", "content": "How are you?"}
    ]
)
```

### 2. Batch Micro-Requests

For high-volume classification or status checks:

```python
# Batch multiple requests to gemma:2b
batch_requests = [
    {"content": "Classify: Email 1"},
    {"content": "Classify: Email 2"},
    {"content": "Classify: Email 3"}
]
```

### 3. Priority Lanes

Implement async queues with priority:

- **High Priority (UI)**: phi3:3.8b, gemma:2b (< 200ms SLA)
- **Medium Priority (background)**: mistral:7b, qwen2.5:3b (< 30s SLA)

### 4. Fallback Strategy

For critical operations, use two-model verification:

```python

# Primary response
response_mistral = await get_response(model="mistral:7b")

# Verification check
verification = await get_response(
    model="phi3:3.8b",
    prompt=f"Check if this answer has hallucinations: {response_mistral}"
)
```

## Monitoring & Metrics

Track these key metrics per model:

| Metric                 | Target                                   |
| ---------------------- | ---------------------------------------- |
| **p50 Latency**        | < 10s (mistral/qwen), < 5s (phi3/gemma)  |
| **p95 Latency**        | < 20s (mistral/qwen), < 10s (phi3/gemma) |
| **Error Rate**         | < 1%                                     |
| **Tokens/Second**      | Varies by model size                     |
| **Cost per 1K tokens** | $0 (self-hosted)                         |

### Evaluation Tests

Run A/B tests to compare models:

```bash
# Test routing decisions
python test_local_routing.py

# Test actual inference
python test_kamatera_llms.py
```

## Safety & Guardrails

All system prompts include safety instructions:

- "Do not invent facts"
- "Label information from external sources"
- "Say 'I don't know' when unsure"

For critical domains (legal, medical), use verification:

1. Primary response from mistral:7b
2. Fact-check with phi3:3.8b
3. Require confidence threshold or model agreement

## Cost Analysis

| Model          | Disk Space | RAM (inference) | Requests/Month | Cloud Cost Equivalent       | Savings |
| -------------- | ---------- | --------------- | -------------- | --------------------------- | ------- |
| **mistral:7b** | 4.4GB      | ~8GB            | Unlimited      | ~$50-100 (Anthropic/OpenAI) | 100%    |
| **qwen2.5:3b** | 1.9GB      | ~4GB            | Unlimited      | ~$30-60 (GPT-3.5)           | 100%    |
| **phi3:3.8b**  | 2.2GB      | ~4GB            | Unlimited      | ~$30-60 (GPT-3.5)           | 100%    |
| **gemma:2b**   | 1.7GB      | ~3GB            | Unlimited      | ~$20-40 (Claude Instant)    | 100%    |

**Total Infrastructure Cost:**

- Kamatera VPS: $15-20/month (2 CPU, 10GB RAM, 20GB disk)
- Cloud LLM Equivalent: $130-260/month
- **Monthly Savings: $110-240**

## Troubleshooting

### Model Selection Not Working

Check that Ollama provider is active in database:

```sql

SELECT * FROM routing_providers WHERE name = 'ollama';
```

### Latency Too High

1. Check CPU usage: `ssh root@45.61.60.3 "htop"`
2. Verify model loaded: `ssh root@45.61.60.3 "ollama ps"`
3. Test direct Ollama: `curl <http://45.61.60.3:8002/health`>

### Wrong Model Selected

Enable routing explanation logging:

```python
result = await routing_service.route_request(...)
print(result["routing_explanation"])
```

## Future Enhancements

Potential improvements:

1. **Quantization**: Compress models (GPTQ/AWQ) to save RAM/disk
2. **Model Ensembling**: Run critical queries on 2 models, compare
3. **Dynamic Batching**: Group similar requests for throughput
4. **Auto-scaling**: Spin up additional workers during peak load
5. **Fine-tuning**: Specialize models for specific domains

## Related Documentation

- [Kamatera LLM Deployment Guide](./KAMATERA_LLM_DEPLOYMENT.md)
- [Ollama Adapter](../providers/ollama_adapter.py)
- [Local LLM Routing Logic](../services/local_llm_routing.py)
- [Test Suite](../test_local_routing.py)

## Support

For questions or issues:

1. Check logs: `ssh root@45.61.60.3 "journalctl -u local-llm-proxy -n 100"`
2. Run diagnostics: `python test_kamatera_llms.py`
3. Review routing decisions: `python test_local_routing.py`
