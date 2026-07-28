"""Provider adapter contracts for orchestration-safe integrations."""

from __future__ import annotations

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Protocol,
    TypedDict,
    runtime_checkable,
)


class ProviderCapabilityLimits(TypedDict, total=False):
    max_input_tokens: int
    max_output_tokens: int
    max_batch_size: int


class ProviderCapabilityMatrix(TypedDict):
    chat: bool
    stream_chat: bool
    health: bool
    capabilities: bool
    embeddings: bool
    limits: ProviderCapabilityLimits


@runtime_checkable
class ProviderAdapter(Protocol):
    """Strict v1 adapter surface consumed by orchestration/dispatch layers."""

    async def chat(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        stream: bool = False,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> Any: ...

    def stream_chat(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]: ...

    async def health(self) -> Any: ...

    def capabilities(self) -> ProviderCapabilityMatrix: ...
