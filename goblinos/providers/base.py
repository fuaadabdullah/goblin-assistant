"""
Base provider interface for Goblin Assistant.
All LLM providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    """Standardized response from any provider."""

    content: str
    usage: Dict[str, int]  # tokens used
    model: str
    finish_reason: str
    metadata: Dict[str, Any]


@dataclass
class StreamChunk:
    """Standardized streaming chunk format."""

    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""

    name: str
    model: str
    max_tokens: int = 4096
    supports_streaming: bool = False
    cost_per_token: float = 0.0

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self._client = None
        self._healthy = True
        self._last_health_check = 0

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate a complete response for the given prompt."""
        pass

    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """Stream response chunks for the given prompt."""
        if not self.supports_streaming:
            raise NotImplementedError(f"{self.name} does not support streaming")
        pass

    @abstractmethod
    def embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for the given texts."""
        pass

    def health_check(self) -> bool:
        """Check if the provider is healthy and available."""
        try:
            # Simple health check - try to get model info or make a minimal request
            return self._healthy
        except Exception:
            self._healthy = False
            return False

    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for given number of tokens."""
        return tokens * self.cost_per_token

    def __str__(self) -> str:
        return f"{self.name}({self.model})"
