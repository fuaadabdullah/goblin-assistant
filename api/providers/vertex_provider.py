"""Vertex AI provider."""

from __future__ import annotations

import json
import os
import time
import base64
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)

_VERTEX_SERVICE_ACCOUNT_FILE = Path("/tmp/goblin_vertex_service_account.json")
_JSON_CONTENT_TYPE = "application/json"


def _parse_google_credentials_payload(payload: str) -> Optional[str]:
    """Return normalized Google credentials JSON string if payload is valid."""
    normalized = payload.strip()
    decoded = normalized

    if not normalized:
        return None

    if not normalized.startswith("{"):
        try:
            decoded = base64.b64decode(normalized).decode("utf-8")
        except Exception:
            decoded = normalized

    try:
        parsed = json.loads(decoded)
        if isinstance(parsed, dict) and parsed.get("type") in {
            "service_account",
            "authorized_user",
            "external_account",
        }:
            return decoded
    except Exception:
        return None
    return None


def _collect_credential_payloads() -> List[str]:
    payloads: List[str] = []
    for key in (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "VERTEX_AI_SERVICE_ACCOUNT_JSON",
        "GCP_SERVICE_ACCOUNT_KEY",
    ):
        value = os.getenv(key, "").strip()
        if value:
            payloads.append(value)
    return payloads


def _configure_google_credentials() -> None:
    """Configure GOOGLE_APPLICATION_CREDENTIALS from supported env formats.

    Supported inputs (in precedence order):
    1. GOOGLE_APPLICATION_CREDENTIALS path (if it exists)
    2. GOOGLE_APPLICATION_CREDENTIALS inline JSON
    3. VERTEX_AI_SERVICE_ACCOUNT_JSON inline JSON or base64 JSON
    4. GCP_SERVICE_ACCOUNT_KEY inline JSON or base64 JSON (legacy)
    """

    existing = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if existing and Path(existing).exists():
        return

    for payload in _collect_credential_payloads():
        decoded = _parse_google_credentials_payload(payload)
        if not decoded:
            continue

        _VERTEX_SERVICE_ACCOUNT_FILE.write_text(decoded, encoding="utf-8")
        os.chmod(_VERTEX_SERVICE_ACCOUNT_FILE, 0o600)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_VERTEX_SERVICE_ACCOUNT_FILE)
        return

_COST_TABLE: Dict[str, Dict[str, float]] = {
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
}


def _get_access_token() -> Optional[str]:
    try:
        _configure_google_credentials()

        import google.auth
        import google.auth.transport.requests

        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
        return creds.token
    except Exception as exc:
        logger.warning("vertex_auth_failed", error=str(exc))
        return None


class VertexAIProvider(BaseProvider):
    COST_INPUT_PER_1K = 0.000075
    COST_OUTPUT_PER_1K = 0.0003

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        self._project = os.getenv(
            "VERTEX_AI_PROJECT",
            os.getenv("GCP_PROJECT_ID", str(self.config.get("project", ""))),
        )
        self._location = os.getenv(
            "VERTEX_AI_LOCATION",
            os.getenv("GCP_REGION", str(self.config.get("location", "us-central1"))),
        )
        self._model = os.getenv(
            "VERTEX_AI_MODEL",
            str(self.config.get("default_model", "gemini-1.5-flash-001")),
        )
        self.endpoint = (
            f"https://{self._location}-aiplatform.googleapis.com/v1"
            f"/projects/{self._project}/locations/{self._location}"
        )

    def _endpoint(self, model: str) -> str:
        return (
            f"https://{self._location}-aiplatform.googleapis.com/v1"
            f"/projects/{self._project}/locations/{self._location}"
            f"/publishers/google/models/{model}:generateContent"
        )

    def _model_cost(self, model: str) -> Dict[str, float]:
        for key, costs in _COST_TABLE.items():
            if key in model:
                return costs
        return {"input": self.COST_INPUT_PER_1K, "output": self.COST_OUTPUT_PER_1K}

    @staticmethod
    def _to_vertex_messages(
        messages: List[Dict[str, str]],
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        system_instruction = None
        contents: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            if role == "system":
                system_instruction = message.get("content", "")
                continue
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": message.get("content", "")}],
                }
            )
        return system_instruction, contents

    async def invoke(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        stream: bool = False,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> ProviderResult:
        normalized_messages = self.normalize_messages(messages, prompt=prompt, **kwargs)
        model_name = model or self._model
        if not self._project:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="VERTEX_AI_PROJECT not set",
            )

        token = _get_access_token()
        if not token:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="Google auth failed",
            )

        system_instruction, contents = self._to_vertex_messages(normalized_messages)
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": _JSON_CONTENT_TYPE,
        }
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    self._endpoint(model_name),
                    headers=headers,
                    json=body,
                )
            latency = (time.perf_counter() - t0) * 1000
            resp.raise_for_status()
            data = resp.json()

            text = ""
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError):
                pass
            usage = data.get("usageMetadata", {})
            costs = self._model_cost(model_name)
            cost = (
                int(usage.get("promptTokenCount", 0)) * costs["input"] / 1000
                + int(usage.get("candidatesTokenCount", 0)) * costs["output"] / 1000
            )
            self.record_success()
            return ProviderResult(
                ok=True,
                text=text,
                raw=data,
                provider=self.provider_id,
                model=model_name,
                usage=usage,
                cost_usd=cost,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            self.record_failure(str(exc))
            logger.warning("vertex_invoke_failed", error=str(exc))
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                latency_ms=latency,
                error=str(exc),
            )

    async def stream(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        normalized_messages = self.normalize_messages(messages, prompt=prompt, **kwargs)
        model_name = model or self._model
        token = _get_access_token()
        if not token:
            return

        system_instruction, contents = self._to_vertex_messages(normalized_messages)
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = self._endpoint(model_name).replace(
            ":generateContent", ":streamGenerateContent"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": _JSON_CONTENT_TYPE,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, headers=headers, json=body) as resp:
                resp.raise_for_status()
                buffer = ""
                async for chunk in resp.aiter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")
                    while buffer:
                        try:
                            obj, idx = json.JSONDecoder().raw_decode(buffer)
                        except json.JSONDecodeError:
                            break
                        buffer = buffer[idx:].lstrip(",\n ")
                        try:
                            text = obj["candidates"][0]["content"]["parts"][0]["text"]
                        except (KeyError, IndexError, TypeError):
                            text = ""
                        if text:
                            yield {"text": text}

    async def health_check(self) -> ProviderHealth:
        if not self._project:
            return ProviderHealth(self.provider_id, False, error="No project")
        token = _get_access_token()
        if not token:
            return ProviderHealth(self.provider_id, False, error="Auth failed")

        t0 = time.perf_counter()
        try:
            body = {
                "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 1},
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._endpoint(self._model),
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": _JSON_CONTENT_TYPE,
                    },
                    json=body,
                )
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                resp.status_code < 400,
                latency_ms=latency,
                error=None if resp.status_code < 400 else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=str(exc),
            )
