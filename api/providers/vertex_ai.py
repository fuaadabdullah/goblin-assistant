"""
Google Cloud Vertex AI provider implementation.

Uses Google AI Gemini API (generativelanguage.googleapis.com) with API key auth.
Provides access to Gemini models including preview versions.

Auth: GOOGLE_AI_API_KEY env var (same key used by the gemini provider).
"""

import os
from typing import AsyncGenerator, Dict, Any, Union
from .base import BaseProvider


class VertexAIProvider(BaseProvider):
    """Google Vertex AI provider using the Gemini API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.gemini_key = os.getenv("GOOGLE_AI_API_KEY", self.api_key or "")
        self.default_model = config.get("default_model", "gemini-2.0-flash")

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
        """Extract text from Gemini response."""
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
        """Invoke Google AI Gemini API."""
        if not self.gemini_key:
            return {"ok": False, "error": "missing-google-ai-api-key", "latency_ms": 0}

        url = (
            f"https://generativelanguage.googleapis.com"
            f"/v1beta/models/{model}:generateContent?key={self.gemini_key}"
        )
        headers = {"Content-Type": "application/json"}

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
