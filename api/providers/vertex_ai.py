"""
Google Cloud Vertex AI provider implementation.

Vertex AI uses Google's Gemini models via the REST API:
- URL: https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/google/models/{MODEL}:generateContent
- Auth: Bearer token from service account key (auto-refreshed) or static token

Supports three auth methods (checked in order):
1. GCP_SERVICE_ACCOUNT_KEY env var (base64-encoded JSON key) — recommended for production
2. GCP_ACCESS_TOKEN env var (static token, 1hr expiry) — for dev/testing
3. gcloud CLI fallback — for local development
"""

import base64
import json
import os
import subprocess
import time
from typing import AsyncGenerator, Dict, Any, Union
from .base import BaseProvider


class VertexAIProvider(BaseProvider):
    """Google Cloud Vertex AI provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.project_id = os.getenv(
            "GCP_PROJECT_ID", config.get("project_id", "")
        )
        self.region = os.getenv(
            "GCP_REGION", config.get("region", "us-central1")
        )
        self.static_token = os.getenv("GCP_ACCESS_TOKEN", "")
        self.sa_key_b64 = os.getenv("GCP_SERVICE_ACCOUNT_KEY", "")
        self.default_model = config.get("default_model", "gemini-2.0-flash")
        self._cached_token = ""
        self._token_expiry = 0.0

    def _get_access_token(self) -> str:
        """Get access token using the best available method."""
        # 1. Service account key — auto-refreshing (best for production)
        if self.sa_key_b64:
            return self._get_token_from_service_account()

        # 2. Static token (short-lived, dev/testing)
        if self.static_token:
            return self.static_token

        # 3. gcloud CLI fallback (local development)
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return ""

    def _get_token_from_service_account(self) -> str:
        """Exchange service account key for an access token via Google OAuth2."""
        # Return cached token if still valid (with 60s buffer)
        if self._cached_token and time.time() < self._token_expiry - 60:
            return self._cached_token

        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            key_json = json.loads(base64.b64decode(self.sa_key_b64))
            credentials = service_account.Credentials.from_service_account_info(
                key_json,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            credentials.refresh(Request())
            self._cached_token = credentials.token
            self._token_expiry = credentials.expiry.timestamp() if credentials.expiry else time.time() + 3600
            return self._cached_token
        except (ImportError, KeyError, ValueError, TypeError):
            return ""

    def _build_url(self, model: str) -> str:
        """Build Vertex AI endpoint URL."""
        base = f"https://{self.region}-aiplatform.googleapis.com"
        return (
            f"{base}/v1/projects/{self.project_id}/locations/{self.region}"
            f"/publishers/google/models/{model}:generateContent"
        )

    def _build_contents(self, prompt: str, **kwargs) -> list:
        """Build Gemini-format contents from messages or prompt."""
        messages = kwargs.get("messages", [])
        if not messages:
            return [{"role": "user", "parts": [{"text": prompt}]}]

        contents = []
        for msg in messages:
            role = "user" if msg.get("role") != "assistant" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}],
            })
        return contents

    @staticmethod
    def _extract_text(data: dict) -> str:
        """Extract text from Vertex AI response."""
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    async def invoke(
        self,
        prompt: str,
        stream: bool = False,
        model: str = "gemini-2.0-flash",
        **kwargs,
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke Vertex AI Gemini API."""
        if not self.project_id:
            return {"ok": False, "error": "missing-gcp-project-id", "latency_ms": 0}

        token = self._get_access_token()
        if not token:
            return {"ok": False, "error": "missing-gcp-access-token", "latency_ms": 0}

        url = self._build_url(model)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "contents": self._build_contents(prompt, **kwargs),
            "generationConfig": {
                "maxOutputTokens": kwargs.get("max_tokens", 512),
                "temperature": kwargs.get("temperature", 0.7),
            },
        }

        result = await self._make_request(
            url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
        )

        if not isinstance(result, dict) or not result.get("ok", False):
            return result if isinstance(result, dict) else {"ok": False, "error": "invalid-response-format", "latency_ms": 0}

        text = self._extract_text(result["result"])
        if not text:
            return {"ok": False, "error": "invalid-response-format", "latency_ms": 0}

        return {
            "ok": True,
            "result": {"text": text, "raw": result["result"]},
            "provider": "vertex_ai",
            "model": model,
            "latency_ms": result["latency_ms"],
        }
