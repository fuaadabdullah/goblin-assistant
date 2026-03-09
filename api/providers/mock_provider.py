"""Mock provider for tests and development."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from .base import BaseProvider, ProviderHealth, ProviderResult


class MockProvider(BaseProvider):
    def __init__(
        self,
        provider_id: str | Dict[str, Any] = "mock",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)

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
        del max_tokens, temperature, kwargs
        normalized_messages = self.normalize_messages(messages, prompt=prompt)
        model_name = model or self.default_model or "mock-gpt"
        processing_time = random.uniform(0.05, 0.2)
        await asyncio.sleep(processing_time)
        latest_prompt = normalized_messages[-1]["content"] if normalized_messages else prompt
        text = self._generate_response(latest_prompt or "", model_name)
        return ProviderResult(
            ok=True,
            text=text,
            raw={"provider": "mock", "model": model_name},
            provider="mock",
            model=model_name,
            latency_ms=processing_time * 1000,
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
        del model, max_tokens, temperature, kwargs
        normalized_messages = self.normalize_messages(messages, prompt=prompt)
        latest_prompt = normalized_messages[-1]["content"] if normalized_messages else prompt
        for word in self._generate_response(latest_prompt or "", "mock-gpt").split():
            await asyncio.sleep(0.01)
            yield {"text": f"{word} "}

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(self.provider_id, True, latency_ms=0.1)

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "mock-embed",
        **kwargs: Any,
    ) -> Union[List[float], List[List[float]]]:
        del model, kwargs
        dim = 32
        is_single = isinstance(texts, str)
        entries = [texts] if is_single else texts
        embeddings = [
            [random.uniform(-1, 1) for _ in range(dim)]
            for _ in entries
        ]
        return embeddings[0] if is_single else embeddings

    def _generate_response(self, prompt: str, model: str) -> str:
        del model
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ("hello", "hi", "hey")):
            return "Hello! This is a mock response for Goblin Assistant."
        if "code" in prompt_lower or "python" in prompt_lower:
            return "Mock response: focus on readable code, validation, and tests."
        if not prompt.strip():
            return "Mock response."
        return f"Mock response to: {prompt[:120]}"
