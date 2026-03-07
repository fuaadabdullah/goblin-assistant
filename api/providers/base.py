"""
Base provider class for all AI model providers.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Union
import time
import httpx


class BaseProvider(ABC):
    """Abstract base class for all AI model providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoint = config.get("endpoint", "")
        self.api_key_env = config.get("api_key_env")
        self.invoke_path = config.get("invoke_path", "")
        self.api_key = self._get_api_key()

    def _get_api_key(self) -> str:
        """Get API key from environment variable."""
        if self.api_key_env:
            import os

            return os.getenv(self.api_key_env, "")
        return ""

    @abstractmethod
    async def invoke(
        self, prompt: str, stream: bool = False, **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """
        Invoke the provider with a prompt.

        Args:
            prompt: The input prompt
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters

        Returns:
            For non-streaming: Dict with result
            For streaming: AsyncGenerator yielding response chunks
        """
        pass

    async def _make_request(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        timeout_ms: int,
        stream: bool = False,
    ) -> Union[httpx.Response, AsyncGenerator[str, None]]:
        """Make HTTP request with proper timeout and error handling."""
        timeout = httpx.Timeout(timeout_ms / 1000.0, read=None)

        async with httpx.AsyncClient(timeout=timeout) as client:
            start_time = time.time()

            try:
                if stream:
                    # For streaming, return the response object for streaming parsing
                    resp = await client.post(
                        url, json=payload, headers=headers, timeout=timeout
                    )
                    if resp.status_code >= 400:
                        return {
                            "ok": False,
                            "error": f"http-{resp.status_code}:{resp.text}",
                            "latency_ms": (time.time() - start_time) * 1000,
                        }
                    return resp
                else:
                    # For non-streaming, return the full response
                    resp = await client.post(
                        url, json=payload, headers=headers, timeout=timeout
                    )
                    latency_ms = (time.time() - start_time) * 1000

                    if resp.status_code >= 400:
                        return {
                            "ok": False,
                            "error": f"http-{resp.status_code}:{resp.text}",
                            "latency_ms": latency_ms,
                        }

                    try:
                        data = resp.json()
                        return {
                            "ok": True,
                            "result": data,
                            "latency_ms": latency_ms,
                        }
                    except Exception as e:
                        return {
                            "ok": False,
                            "error": f"json-parse-error:{str(e)}",
                            "latency_ms": latency_ms,
                        }

            except Exception as e:
                return {
                    "ok": False,
                    "error": str(e),
                    "latency_ms": (time.time() - start_time) * 1000,
                }

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "",
        **kwargs,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings. Override in providers that support embeddings."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support embeddings"
        )

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "BaseProvider":
        """Factory method to create provider instance from config."""
        return cls(config)
