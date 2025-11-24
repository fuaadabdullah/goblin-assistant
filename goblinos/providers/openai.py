"""
OpenAI provider implementation for Goblin Assistant.
"""

import os
import json
import httpx
from typing import List, AsyncGenerator, Optional
from .base import BaseProvider, ProviderResponse, StreamChunk


class OpenAIProvider(BaseProvider):
    """OpenAI API provider implementation using httpx."""

    name = "openai"
    supports_streaming = True
    cost_per_token = 0.000002  # GPT-4 approximate cost per token

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", **kwargs):
        super().__init__(api_key, **kwargs)
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.organization = kwargs.get("organization")
        self.endpoint = "https://api.openai.com/v1"

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

    def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate a complete response using OpenAI."""
        import asyncio

        try:
            return asyncio.run(self._generate_async(prompt, **kwargs))
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {e}")

    async def _generate_async(self, prompt: str, **kwargs) -> ProviderResponse:
        """Async implementation of generate."""
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", 0.7)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization:
            headers["OpenAI-Organization"] = self.organization

        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.endpoint}/chat/completions", headers=headers, json=body
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )

            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return ProviderResponse(
                content=choice["message"]["content"],
                usage=usage,
                model=data.get("model", self.model),
                finish_reason=choice.get("finish_reason"),
                metadata={"provider": self.name},
            )

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """Stream response from OpenAI."""
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", 0.7)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization:
            headers["OpenAI-Organization"] = self.organization

        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=None)) as client:
            async with client.stream(
                "POST", f"{self.endpoint}/chat/completions", headers=headers, json=body
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(
                        f"OpenAI API error: {response.status_code} - {error_text.decode()}"
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break

                        try:
                            chunk_data = json.loads(data)
                            if chunk_data.get("choices"):
                                choice = chunk_data["choices"][0]
                                delta = choice.get("delta", {})
                                content = delta.get("content", "")

                                if content:
                                    yield StreamChunk(
                                        content=content,
                                        finish_reason=choice.get("finish_reason"),
                                    )

                                # Send usage info if available
                                if choice.get("finish_reason") and chunk_data.get(
                                    "usage"
                                ):
                                    yield StreamChunk(
                                        content="",
                                        finish_reason=choice["finish_reason"],
                                        usage=chunk_data["usage"],
                                    )
                        except json.JSONDecodeError:
                            continue

    def embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI."""
        import asyncio

        try:
            return asyncio.run(self._embeddings_async(texts))
        except Exception as e:
            raise RuntimeError(f"OpenAI embeddings failed: {e}")

    async def _embeddings_async(self, texts: List[str]) -> List[List[float]]:
        """Async implementation of embeddings."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization:
            headers["OpenAI-Organization"] = self.organization

        body = {"model": "text-embedding-3-small", "input": texts}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.endpoint}/embeddings", headers=headers, json=body
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )

            data = response.json()
            return [item["embedding"] for item in data["data"]]

    def health_check(self) -> bool:
        """Check OpenAI API health."""
        import asyncio

        try:
            asyncio.run(self._health_check_async())
            self._healthy = True
            return True
        except Exception:
            self._healthy = False
            return False

    async def _health_check_async(self) -> None:
        """Async health check."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.organization:
            headers["OpenAI-Organization"] = self.organization

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.endpoint}/models", headers=headers)

            if response.status_code != 200:
                raise RuntimeError(f"Health check failed: {response.status_code}")

            data = response.json()
            if not data.get("data"):
                raise RuntimeError("No models available")
