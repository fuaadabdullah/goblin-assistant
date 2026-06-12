#!/usr/bin/env python3
"""Direct probe of Aliyun DashScope (compat mode) API + dispatcher path."""

import asyncio
import os
import sys
import time
from pathlib import Path

import httpx

# Load env from apps/api/.env.local
ROOT = Path(__file__).resolve().parents[3]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT / ".env")
except Exception:
    pass

API_KEY = os.getenv("DASHSCOPE_API_KEY", "").strip()
BASE = os.getenv(
    "DASHSCOPE_ENDPOINT", "https://dashscope-intl.aliyuncs.com/compatible-mode"
).rstrip("/")
if BASE.endswith("/v1"):
    BASE = BASE[:-3]


async def probe_models() -> bool:
    url = f"{BASE}/v1/models"
    print(f"\n📡 GET {url}")
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
    print(f"   status={r.status_code}")
    print(f"   body[:300]={r.text[:300]}")
    return r.status_code < 400


async def probe_chat() -> bool:
    url = f"{BASE}/v1/chat/completions"
    body = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "Say 'pong' and nothing else."}],
        "max_tokens": 20,
        "temperature": 0.1,
    }
    print(f"\n📡 POST {url}  model=qwen-plus")
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            url,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    dt = (time.perf_counter() - t0) * 1000
    print(f"   status={r.status_code}  latency={dt:.0f}ms")
    if r.status_code >= 400:
        print(f"   error body: {r.text[:400]}")
        return False
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    print(f"   response: {text!r}")
    return True


async def probe_dispatcher() -> bool:
    sys.path.insert(0, str(ROOT / "src"))
    from api.providers.dispatcher import ProviderDispatcher  # noqa: E402

    d = ProviderDispatcher()
    print("\n🔧 dispatcher.check_provider('aliyun') ...")
    health = await d.check_provider("aliyun")
    print(f"   {health}")
    print("\n🔧 dispatcher.invoke_provider(aliyun, qwen-plus) ...")
    res = await d.invoke_provider(
        pid="aliyun",
        model="qwen-plus",
        payload={"messages": [{"role": "user", "content": "Say pong."}]},
        timeout_ms=30_000,
    )
    print(f"   ok={res.get('ok')}  provider={res.get('provider')}  err={res.get('error')}")
    print(f"   text={(res.get('text') or '')[:120]!r}")
    return bool(res.get("ok"))


async def main() -> int:
    print("=" * 60)
    print("Aliyun DashScope live probe")
    print("=" * 60)
    if not API_KEY:
        print("❌ DASHSCOPE_API_KEY missing")
        return 1
    print(f"key: {API_KEY[:10]}…{API_KEY[-4:]}  base: {BASE}")

    models_ok = await probe_models()
    chat_ok = await probe_chat()
    dispatcher_ok = await probe_dispatcher()

    print("\n" + "=" * 60)
    print(f"models endpoint: {'✅' if models_ok else '❌'}")
    print(f"chat completion: {'✅' if chat_ok else '❌'}")
    print(f"dispatcher path: {'✅' if dispatcher_ok else '❌'}")
    print("=" * 60)
    return 0 if (chat_ok and dispatcher_ok) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
