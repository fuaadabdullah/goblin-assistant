# Colab Worker Runbook

This runbook describes how to run a disposable Colab-hosted inference worker and connect it to Goblin as provider `colab_worker`.

## Operational constraints

- Colab is ephemeral. Treat it as disposable compute only.
- Persistence must stay in Goblin storage (Postgres + existing memory/task/chat stores).
- If Colab dies, Goblin falls back to other configured providers when `colab_worker` is explicitly selected.

---

## 1. Check your GPU

Before anything else, verify what GPU you got:

```python
!nvidia-smi
```

- **T4 (16 GB)** — fast, use it.
- **K80 (12 GB)** — ~3× slower than T4. Disconnect and reconnect the runtime repeatedly until you get a T4. Not elegant, but effective.
- Once you have a T4, keep the runtime alive (see §5) to avoid losing it.

---

## 2. Install dependencies

```python
!CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python huggingface_hub fastapi uvicorn
```

The `CMAKE_ARGS` flag compiles llama-cpp-python with CUDA support so all model layers can be offloaded to the GPU.

---

## 3. Download the model

Download a GGUF-quantized model directly from Hugging Face. This is faster than loading from Google Drive and the file is cached in Colab's ephemeral SSD for the lifetime of the runtime.

```python
from huggingface_hub import hf_hub_download

# Default: fast/general chat and research
model_path = hf_hub_download(
    repo_id="bartowski/gemma-3-12b-it-GGUF",
    filename="gemma-3-12b-it-Q4_K_M.gguf",
    cache_dir="/tmp/hf_cache",
)

# Alternate: coding / planning / agent tasks
# model_path = hf_hub_download(
#     repo_id="bartowski/Qwen3-14B-GGUF",
#     filename="Qwen3-14B-Q4_K_M.gguf",
#     cache_dir="/tmp/hf_cache",
# )

print(model_path)
```

A 4 GB file typically downloads in 15–30 seconds on Colab's connection.

---

## 4. Start the inference server

### Option A — built-in OpenAI-compatible server (simplest)

```python
import subprocess
proc = subprocess.Popen([
    "python", "-m", "llama_cpp.server",
    "--model", model_path,
    "--n_gpu_layers", "-1",   # offload all layers to GPU
    "--n_ctx", "2048",
    "--host", "0.0.0.0",
    "--port", "8000",
])
```

This serves `/v1/chat/completions`, `/v1/models`, and `/v1/completions` — the Goblin provider hits `/v1/chat/completions` by default.

### Option B — FastAPI wrapper with concurrency guard (recommended)

Use this when you want a `/health` endpoint and protection against GPU saturation:

```python
import asyncio
import os
from fastapi import FastAPI, Header, HTTPException
from llama_cpp import Llama

app = FastAPI()
sem = asyncio.Semaphore(2)  # max 2 concurrent generations

API_KEY = os.environ["COLAB_WORKER_API_KEY"]

llm = Llama(
    model_path=model_path,
    n_gpu_layers=-1,    # offload all layers
    n_ctx=2048,         # keep context short to save VRAM
    n_batch=512,
    use_mlock=True,
    use_mmap=True,
)

def _auth(authorization: str | None) -> None:
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="unauthorized")

@app.get("/health")
def health(authorization: str | None = Header(default=None)):
    _auth(authorization)
    return {"healthy": True}

@app.post("/v1/chat/completions")
async def chat(req: dict, authorization: str | None = Header(default=None)):
    _auth(authorization)
    messages = req.get("messages") or []
    prompt = "\n".join(m.get("content", "") for m in messages if isinstance(m, dict))
    async with sem:
        output = llm(prompt, max_tokens=req.get("max_tokens", 512))
    text = output["choices"][0]["text"]
    return {
        "id": "chatcmpl-colab",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

@app.get("/v1/models")
def models(authorization: str | None = Header(default=None)):
    _auth(authorization)
    return {"object": "list", "data": [{"id": "gemma-3-12b", "object": "model"}]}

import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
```

Set the API key first:

```python
import os
os.environ["COLAB_WORKER_API_KEY"] = "replace_with_long_random_token"
```

---

## 5. Keep the runtime alive

### Browser console (quick)

Open DevTools (F12) in the Colab tab, paste into the console:

```javascript
function clickConnect() {
    document.querySelector('#top-toolbar > colab-connect-button')
        .shadowRoot.querySelector('#connect').click()
}
setInterval(clickConnect, 60000)
```

This clicks the Connect button every 60 seconds to prevent idle disconnection.

### External ping (robust)

Configure [UptimeRobot](https://uptimerobot.com) or a Replit cron to `GET` your tunnel URL `/health` every 5 minutes. This both prevents idle timeout and gives you an early warning when the runtime dies.

---

## 6. Expose via Cloudflare Tunnel

Cloudflare Tunnel has lower latency and a more stable free tier than ngrok.

```python
import subprocess, threading, re

!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
!chmod +x cloudflared

proc = subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", "http://localhost:8000"],
    stderr=subprocess.PIPE,
    text=True,
)

# Parse the public URL from cloudflared output
for line in proc.stderr:
    m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
    if m:
        print("Tunnel URL:", m.group(0))
        break
```

Use the printed URL as `COLAB_WORKER_ENDPOINT` in your backend.

---

## 7. Backend environment

Set these in the backend runtime (Render / local):

```bash
COLAB_WORKER_ENDPOINT=https://abc123.trycloudflare.com
COLAB_WORKER_API_KEY=replace_with_long_random_token
COLAB_WORKER_HEARTBEAT_ENABLED=true
COLAB_WORKER_HEARTBEAT_INTERVAL_SECONDS=60
```

---

## 8. Verify from backend host

```bash
# Health check
curl -s -H "Authorization: Bearer $COLAB_WORKER_API_KEY" \
  "$COLAB_WORKER_ENDPOINT/health"

# Model list
curl -s -H "Authorization: Bearer $COLAB_WORKER_API_KEY" \
  "$COLAB_WORKER_ENDPOINT/v1/models"

# Generation
curl -s -X POST "$COLAB_WORKER_ENDPOINT/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COLAB_WORKER_API_KEY" \
  -d '{"model":"gemma-3-12b","messages":[{"role":"user","content":"Explain options trading"}]}'
```

---

## Model selection policy

- Default model: `gemma-3-12b` — fast, general chat/research.
- Alternate model: `qwen3-14b` — coding, planning, and agent tasks; select explicitly by model name.
- Load the model that matches your current workload at notebook startup; switching requires a runtime restart.
