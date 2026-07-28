from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest

from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.contracts import ProviderAdapter


class _StubProvider(BaseProvider):
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
        del messages, model, stream, max_tokens, temperature, prompt, kwargs
        return ProviderResult(ok=True, text="ok", provider="stub", model="stub")

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_id="stub", healthy=True)

    async def embed(
        self,
        texts: str | List[str],
        model: str = "",
        **kwargs: Any,
    ) -> List[float] | List[List[float]]:
        del model, kwargs
        if isinstance(texts, str):
            return [0.1, 0.2]
        return [[0.1, 0.2] for _ in texts]

    async def _stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"token": "ok"}

    def stream(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        del messages, model, max_tokens, temperature, prompt, kwargs
        return self._stream()


@pytest.mark.asyncio
async def test_base_provider_implements_v1_adapter_surface():
    provider: ProviderAdapter = _StubProvider(
        "stub",
        {
            "capabilities": ["chat", "embeddings"],
            "max_input_tokens": 4096,
        },
    )

    result = await provider.chat(prompt="hello")
    assert result.ok is True

    health = await provider.health()
    assert health.healthy is True

    capabilities = provider.capabilities()
    assert capabilities["chat"] is True
    assert capabilities["health"] is True
    assert capabilities["capabilities"] is True
    assert capabilities["stream_chat"] is True
    assert capabilities["embeddings"] is True
    assert capabilities["limits"]["max_input_tokens"] == 4096
