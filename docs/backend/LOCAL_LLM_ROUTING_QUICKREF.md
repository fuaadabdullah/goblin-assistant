# Local LLM Routing - Quick Reference Card

## 🎯 Model Selection Cheat Sheet

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENT ROUTING RULES                    │
└─────────────────────────────────────────────────────────────────┘

📊 GEMMA:2B (1.7GB, 8K context, ~5-8s)
   ├─ Ultra-low latency (< 100ms target)
   ├─ Classification tasks
   ├─ Status checks / health endpoints
   ├─ Cost-priority mode (< 100 tokens)
   └─ Params: temp=0.0, max_tokens=40

💬 PHI3:3.8B (2.2GB, 4K context, ~10-12s)
   ├─ Low latency chat (100-200ms target)
   ├─ Conversational UI
   ├─ Multi-turn dialogues
   ├─ Quick Q&A
   └─ Params: temp=0.15, max_tokens=128

📚 QWEN2.5:3B (1.9GB, 32K context, ~14s)
   ├─ Long context (> 8K tokens)
   ├─ Multilingual content
   ├─ RAG / document retrieval
   ├─ Translation tasks
   └─ Params: temp=0.0-0.3, max_tokens=1024

⭐ MISTRAL:7B (4.4GB, 8K context, ~14-15s)
   ├─ Code generation
   ├─ Creative writing
   ├─ Detailed explanations
   ├─ Legal / compliance
   └─ Params: temp=0.0-0.6, max_tokens=512
```

## 🔑 Intent Keywords

| Intent             | Trigger Words                            | Route To   |
| ------------------ | ---------------------------------------- | ---------- |
| **code-gen**       | code, function, implement, script, class | mistral:7b |
| **creative**       | story, poem, creative, imagine           | mistral:7b |
| **explain**        | explain, what is, how does               | mistral:7b |
| **summarize**      | summarize, summary, tldr                 | mistral:7b |
| **rag**            | based on, according to, from document    | qwen2.5:3b |
| **translation**    | translate, say in, translation           | qwen2.5:3b |
| **chat**           | conversational flow, Q&A                 | phi3:3.8b  |
| **classification** | classify, category, label                | gemma:2b   |
| **status**         | status, health, check                    | gemma:2b   |

## 🚀 Quick API Examples

### 1. Code Generation (mistral:7b)

```python
{
    "messages": [
        {"role": "user", "content": "Write a function to validate email"}
    ]
}
# → Routes to mistral:7b with temp=0.0
```

### 2. Fast Status Check (gemma:2b)

```python

{
    "messages": [
        {"role": "user", "content": "Is the service healthy?"}
    ],
    "latency_target": "ultra_low"
}

# → Routes to gemma:2b with temp=0.0, max_tokens=40
```

### 3. Long Document RAG (qwen2.5:3b)

```python
{
    "messages": [
        {"role": "user", "content": "Summarize this 50-page report"}
    ],
    "context": "<large document>",
    "intent": "rag"
}
# → Routes to qwen2.5:3b with temp=0.0, max_tokens=1024
```

### 4. Conversational Chat (phi3:3.8b)

```python

{
    "messages": [
        {"role": "user", "content": "Hi, can you help?"},
        {"role": "assistant", "content": "Of course!"},
        {"role": "user", "content": "I need advice on..."}
    ],
    "latency_target": "low"
}

# → Routes to phi3:3.8b with temp=0.15, max_tokens=128
```

## 📊 Performance SLAs

| Model      | p50 Latency | p95 Latency | Best For               |
| ---------- | ----------- | ----------- | ---------------------- |
| gemma:2b   | 5s          | 8s          | Status, classification |
| phi3:3.8b  | 10s         | 12s         | Chat, UI responses     |
| qwen2.5:3b | 14s         | 18s         | Long docs, RAG         |
| mistral:7b | 14s         | 20s         | High quality, code     |

## 🎛️ Parameter Presets

```python
# Code generation (mistral)
{"temperature": 0.0, "top_p": 0.95, "max_tokens": 512}

# Creative writing (mistral)
{"temperature": 0.6, "top_p": 0.95, "max_tokens": 512}

# RAG retrieval (qwen2.5)
{"temperature": 0.0, "top_p": 0.9, "max_tokens": 1024}

# Conversational (phi3)
{"temperature": 0.15, "top_p": 0.9, "max_tokens": 128}

# Classification (gemma)
{"temperature": 0.0, "top_p": 0.9, "max_tokens": 40}
```

## 🔍 Override Routing

Force specific model:

```python

{
    "messages": [...],
    "intent": "creative",           # Force mistral:7b
    "latency_target": "ultra_low",  # Force gemma:2b
    "cost_priority": true           # Prefer cheaper models
}
```

## 💡 Tips

1. **Batch micro-tasks** (classification) to gemma:2b
2. **Use KV cache** for multi-turn chats (phi3)
3. **Explicit intent** overrides auto-detection
4. **Cost priority** for high-volume low-stakes queries
5. **Two-model verification** for critical operations

## 📞 Quick Test

```bash
# Test routing logic
python backend/test_local_routing.py

# Test actual inference
python backend/test_kamatera_llms.py
```

## 🌐 Endpoint

```
POST http://45.61.60.3:8002/v1/chat/completions
Headers: x-api-key: your-secure-api-key-here
```

---

**Cost**: $0/request (self-hosted) | **Uptime**: 99.9% | **Rate Limits**: None
