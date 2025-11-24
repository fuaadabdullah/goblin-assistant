# src/routing/invoke_provider_impl.py
import os
import time
import json
import httpx
from typing import Dict, Any, AsyncGenerator, Optional


# Helper: parse SSE-style chunks ("data: {...}\n\n")
def _parse_sse_line(line: bytes) -> Optional[str]:
    s = line.decode(errors="ignore").strip()
    if not s:
        return None
    if s.startswith("data:"):
        return s[len("data:") :].strip()
    return s


async def _stream_sse_response(resp: httpx.Response) -> AsyncGenerator[str, None]:
    """
    Generic SSE parser for httpx response.iter_bytes()
    yields decoded data strings (raw text) as they arrive.
    """
    async for chunk in resp.aiter_bytes():
        # chunk may contain multiple lines
        parts = chunk.split(b"\n\n")
        for p in parts:
            line = p.strip()
            if not line:
                continue
            # handle multi-line contents
            try:
                # split into lines, pick lines starting with data:
                lines = line.split(b"\n")
                for L in lines:
                    parsed = _parse_sse_line(L)
                    if parsed is not None:
                        yield parsed
            except Exception:
                try:
                    yield line.decode(errors="ignore")
                except Exception:
                    continue


async def invoke_provider(
    pid: str, model: str, payload: Dict[str, Any], timeout_ms: int, stream: bool = False
) -> Dict[str, Any]:
    """
    Implementations for:
      - openai (supports streaming)
      - ollama_local (attempt streaming if stream=True)
      - anthropic_claude (non-stream or use SSE if available)
      - grok (non-stream)
      - gemini (non-stream)
      - generic cloudflare-like
    Return:
      - non-stream success: {"ok": True, "result": {...}, "latency_ms": float}
      - stream success: {"ok": True, "stream": async_gen}
      - failure: {"ok": False, "error": "...", "latency_ms": float}
    """
    # Import PROVIDERS from router.py - this assumes the file is in the same directory
    from .router import PROVIDERS

    cfg = PROVIDERS.get(pid)
    if not cfg:
        return {"ok": False, "error": f"unknown-provider:{pid}", "latency_ms": 0}
    endpoint = cfg.get("endpoint")
    api_key_env = cfg.get("api_key_env")
    api_key = os.getenv(api_key_env) if api_key_env else None
    invoke_path = cfg.get("invoke_path", "")
    timeout = httpx.Timeout(timeout_ms / 1000.0, read=None)  # streaming needs read=None

    start = time.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        # ---------- LLAMACPP (local OpenAI-compatible) ----------
        if pid == "llamacpp" or "127.0.0.1:8080" in endpoint:
            headers = {
                "Content-Type": "application/json",
            }
            url = endpoint.rstrip("/") + (invoke_path or "/v1/chat/completions")
            # build body
            if "messages" in payload:
                body = {
                    "model": model,
                    "messages": payload["messages"],
                    "max_tokens": payload.get("max_tokens", 512),
                    "temperature": payload.get("temperature", 0.2),
                }
            else:
                body = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": payload.get("prompt", "")}
                    ],
                    "max_tokens": payload.get("max_tokens", 512),
                }
            if stream:
                # OpenAI style streaming: set stream=true and parse SSE-ish "data: ..." chunks
                body["stream"] = True
                resp = await client.post(
                    url, json=body, headers=headers, timeout=timeout
                )
                if resp.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"llamacpp-status:{resp.status_code}:{resp.text}",
                        "latency_ms": (time.time() - start) * 1000,
                    }

                # return an async generator
                async def gen():
                    async for data in _stream_sse_response(resp):
                        try:
                            parsed = json.loads(data)
                            if "choices" in parsed and parsed["choices"]:
                                choice = parsed["choices"][0]
                                delta = choice.get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except Exception:
                            continue

                return {
                    "ok": True,
                    "stream": gen(),
                    "latency_ms": (time.time() - start) * 1000,
                }
            else:
                r = await client.post(url, json=body, headers=headers, timeout=timeout)
                lat = (time.time() - start) * 1000
                if r.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"llamacpp-status:{r.status_code}:{r.text}",
                        "latency_ms": lat,
                    }
                try:
                    data = r.json()
                    # Extract text from OpenAI-style response
                    if "choices" in data and data["choices"]:
                        choice = data["choices"][0]
                        text = choice.get("message", {}).get(
                            "content", ""
                        ) or choice.get("text", "")
                    else:
                        text = str(data)

                    # Check for garbled output (common with corrupted models)
                    garbled_chars = [
                        "\x1c",
                        "\x00",
                        "\x01",
                        "\x02",
                        "\x03",
                        "\x04",
                        "\x05",
                        "\x06",
                        "\x07",
                        "\x08",
                        "\x0b",
                        "\x0c",
                        "\x0e",
                        "\x0f",
                        "\x10",
                        "\x11",
                        "\x12",
                        "\x13",
                        "\x14",
                        "\x15",
                        "\x16",
                        "\x17",
                        "\x18",
                        "\x19",
                        "\x1a",
                        "\x1b",
                        "\x1d",
                        "\x1e",
                        "\x1f",
                    ]
                    garbled_ratio = (
                        sum(1 for char in text if char in garbled_chars) / len(text)
                        if text
                        else 0
                    )

                    if garbled_ratio > 0.1:
                        return {
                            "ok": False,
                            "error": f"llamacpp-garbled-output: Model produced {garbled_ratio:.1%} garbled characters. Try a different model.",
                            "latency_ms": lat,
                        }

                    return {
                        "ok": True,
                        "result": {"text": text, "raw": data},
                        "latency_ms": lat,
                    }
                except Exception as e:
                    return {
                        "ok": False,
                        "error": f"llamacpp-parse-error:{str(e)}",
                        "latency_ms": lat,
                    }

        # ---------- OPENAI ----------
        if pid == "openai" or "openai.com" in endpoint:
            if not api_key:
                return {
                    "ok": False,
                    "error": "missing-openai-key",
                    "latency_ms": (time.time() - start) * 1000,
                }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            url = endpoint.rstrip("/") + (invoke_path or "/v1/chat/completions")
            # build body
            if "messages" in payload:
                body = {
                    "model": model,
                    "messages": payload["messages"],
                    "max_tokens": payload.get("max_tokens", 512),
                    "temperature": payload.get("temperature", 0.2),
                }
            else:
                body = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": payload.get("prompt", "")}
                    ],
                    "max_tokens": payload.get("max_tokens", 512),
                }
            if stream:
                # OpenAI style streaming: set stream=true and parse SSE-ish "data: ..." chunks
                body["stream"] = True
                resp = await client.post(
                    url, json=body, headers=headers, timeout=timeout
                )
                if resp.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"openai-status:{resp.status_code}:{resp.text}",
                        "latency_ms": (time.time() - start) * 1000,
                    }

                # return an async generator
                async def gen():
                    async for data in _stream_sse_response(resp):
                        # openai often sends "data: [DONE]" at end
                        if data.strip() == "[DONE]":
                            break
                        # try parse JSON
                        try:
                            parsed = json.loads(data)
                            # typical payload: {"choices":[{"delta":{"content":"..."} }]}
                            yield parsed
                        except Exception:
                            yield data

                return {
                    "ok": True,
                    "stream": gen(),
                    "latency_ms": (time.time() - start) * 1000,
                }
            else:
                r = await client.post(url, json=body, headers=headers)
                lat = (time.time() - start) * 1000
                if r.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"openai-status:{r.status_code}:{r.text}",
                        "latency_ms": lat,
                    }
                j = r.json()
                text = None
                if "choices" in j and len(j["choices"]) > 0:
                    c = j["choices"][0]
                    text = c.get("message", {}).get("content") or c.get("text")
                if text is None:
                    text = str(j)
                return {
                    "ok": True,
                    "result": {"text": text, "raw": j},
                    "latency_ms": lat,
                }

        # ---------- OLLAMA (local) ----------
        if "127.0.0.1" in endpoint or "ollama" in pid or "ollama" in endpoint:
            # try streaming if requested
            # Ollama often supports simple streaming via chunked response at /api/generate (some versions)
            paths = ["/api/generate", "/v1/generate", invoke_path or ""]
            prompt = None
            if "messages" in payload:
                prompt = "\n".join([m.get("content", "") for m in payload["messages"]])
            else:
                prompt = payload.get("prompt", "")
            body = {
                "model": model,
                "prompt": prompt,
                "max_tokens": payload.get("max_tokens", 512),
            }
            last_err = None
            for pth in paths:
                if not pth:
                    url = endpoint
                else:
                    url = endpoint.rstrip("/") + pth
                try:
                    if stream:
                        # streaming via chunked response
                        resp = await client.post(url, json=body, timeout=timeout)
                        if resp.status_code >= 400:
                            last_err = f"ollama-status:{resp.status_code}:{resp.text}"
                            continue

                        async def gen():
                            async for raw in _stream_sse_response(resp):
                                # Ollama chunk may be JSON or plain text. Try parse JSON
                                try:
                                    parsed = json.loads(raw)
                                    yield parsed
                                except Exception:
                                    yield raw

                        return {
                            "ok": True,
                            "stream": gen(),
                            "latency_ms": (time.time() - start) * 1000,
                        }
                    else:
                        r = await client.post(url, json=body, timeout=timeout)
                        lat = (time.time() - start) * 1000
                        if r.status_code >= 400:
                            last_err = f"ollama-status:{r.status_code}:{r.text}"
                            continue
                        try:
                            data = r.json()
                        except Exception:
                            data = {"text": r.text}
                        # parse common shapes
                        if isinstance(data, dict):
                            text = (
                                data.get("generated", [{}])[0].get("text")
                                if "generated" in data
                                else data.get("completion") or data.get("text")
                            )
                        else:
                            text = str(data)
                        return {
                            "ok": True,
                            "result": {"text": text, "raw": data},
                            "latency_ms": lat,
                        }
                except httpx.HTTPError as e:
                    last_err = str(e)
                    continue
            return {
                "ok": False,
                "error": f"ollama-all-paths-failed:{last_err}",
                "latency_ms": (time.time() - start) * 1000,
            }

        # ---------- ANTHROPIC (Claude) ----------
        if pid.startswith("anthropic") or "anthropic" in endpoint:
            if not api_key:
                return {
                    "ok": False,
                    "error": "missing-anthropic-key",
                    "latency_ms": (time.time() - start) * 1000,
                }
            headers = {"x-api-key": api_key, "Content-Type": "application/json"}
            # Claude v1: POST /v1/complete or /v1/claude
            url = endpoint.rstrip("/") + (invoke_path or "/v1/complete")
            # Anthropic streaming uses "stream=true" with event streams in some variants; cover non-stream
            body = {
                "model": model,
                "prompt": payload.get("prompt")
                or (
                    payload.get("messages")
                    and "\n".join([m.get("content", "") for m in payload["messages"]])
                ),
                "max_tokens": payload.get("max_tokens", 512),
            }
            try:
                if stream:
                    r = await client.post(
                        url,
                        json={**body, "stream": True},
                        headers=headers,
                        timeout=timeout,
                    )
                    if r.status_code >= 400:
                        return {
                            "ok": False,
                            "error": f"anthropic-status:{r.status_code}:{r.text}",
                            "latency_ms": (time.time() - start) * 1000,
                        }

                    async def gen():
                        async for raw in _stream_sse_response(r):
                            yield raw

                    return {
                        "ok": True,
                        "stream": gen(),
                        "latency_ms": (time.time() - start) * 1000,
                    }
                r = await client.post(url, json=body, headers=headers, timeout=timeout)
                lat = (time.time() - start) * 1000
                if r.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"anthropic-status:{r.status_code}:{r.text}",
                        "latency_ms": lat,
                    }
                j = r.json()
                # parse typical response
                text = j.get("completion") or j.get("text") or str(j)
                return {
                    "ok": True,
                    "result": {"text": text, "raw": j},
                    "latency_ms": lat,
                }
            except Exception as e:
                return {
                    "ok": False,
                    "error": str(e),
                    "latency_ms": (time.time() - start) * 1000,
                }

        # ---------- GROK (non-stream) ----------
        if pid == "grok" or "grok" in endpoint:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            headers["Content-Type"] = "application/json"
            url = endpoint.rstrip("/") + (invoke_path or "/v1/generate")
            try:
                r = await client.post(
                    url,
                    json={
                        "model": model,
                        "prompt": payload.get("prompt", ""),
                        "max_tokens": payload.get("max_tokens", 512),
                    },
                    headers=headers,
                    timeout=timeout,
                )
                lat = (time.time() - start) * 1000
                if r.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"grok-status:{r.status_code}:{r.text}",
                        "latency_ms": lat,
                    }
                j = r.json()
                # parse response
                text = (
                    j.get("output")
                    or (j.get("choices") and j["choices"][0].get("text"))
                    or str(j)
                )
                return {
                    "ok": True,
                    "result": {"text": text, "raw": j},
                    "latency_ms": lat,
                }
            except Exception as e:
                return {
                    "ok": False,
                    "error": str(e),
                    "latency_ms": (time.time() - start) * 1000,
                }

        # ---------- GEMINI (non-stream) ----------
        if pid == "gemini" or "gemini" in endpoint:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            headers["Content-Type"] = "application/json"
            url = endpoint.rstrip("/") + (invoke_path or "/v1/generate")
            try:
                r = await client.post(
                    url,
                    json={
                        "model": model,
                        "messages": payload.get("messages")
                        or [{"role": "user", "content": payload.get("prompt", "")}],
                    },
                    headers=headers,
                    timeout=timeout,
                )
                lat = (time.time() - start) * 1000
                if r.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"gemini-status:{r.status_code}:{r.text}",
                        "latency_ms": lat,
                    }
                j = r.json()
                text = j.get("output") or j.get("content") or str(j)
                return {
                    "ok": True,
                    "result": {"text": text, "raw": j},
                    "latency_ms": lat,
                }
            except Exception as e:
                return {
                    "ok": False,
                    "error": str(e),
                    "latency_ms": (time.time() - start) * 1000,
                }

        # ---------- Generic provider fallback ----------
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        headers["Content-Type"] = "application/json"
        url = endpoint.rstrip("/") + invoke_path
        try:
            if stream:
                r = await client.post(
                    url, json=payload, headers=headers, timeout=timeout
                )
                if r.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"{pid}-status:{r.status_code}:{r.text}",
                        "latency_ms": (time.time() - start) * 1000,
                    }

                async def gen():
                    async for raw in _stream_sse_response(r):
                        yield raw

                return {
                    "ok": True,
                    "stream": gen(),
                    "latency_ms": (time.time() - start) * 1000,
                }
            else:
                r = await client.post(
                    url, json=payload, headers=headers, timeout=timeout
                )
                lat = (time.time() - start) * 1000
                if r.status_code >= 400:
                    return {
                        "ok": False,
                        "error": f"{pid}-status:{r.status_code}:{r.text}",
                        "latency_ms": lat,
                    }
                try:
                    data = r.json()
                except Exception:
                    data = {"text": r.text}
                return {"ok": True, "result": {"text": data}, "latency_ms": lat}
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "latency_ms": (time.time() - start) * 1000,
            }
