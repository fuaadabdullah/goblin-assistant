"""Google Cloud Self-Hosted provider family.

Unifies Ollama GCP, LlamaCPP GCP, Colab Worker, and Vertex AI under a single
provider.  Backends are defined in providers.toml as an array of tables under
``providers.google_cloud_selfhosted.backends``; each entry carries an
``engine``
field that selects the implementation class.

Backend failover is ordered by the ``priority`` field (lower = tried first).
``invoke`` and ``stream`` return the first successful backend response.
``health_check`` polls all backends concurrently and reports aggregate health.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Type

import structlog

from .base import (
    BaseProvider,
    ProviderHealth,
    ProviderResult,
    classify_provider_error,
)
from .colab_worker_provider import ColabWorkerProvider
from .llamacpp_provider import LlamaCPPProvider
from .ollama_provider import OllamaProvider
from .vertex_provider import VertexAIProvider

logger = structlog.get_logger(__name__)


def _backend_is_configured(bc: Dict[str, Any]) -> bool:
    """Return True if the backend's primary env var is present and non-empty."""
    for key in ("endpoint_env", "project_env", "api_key_env"):
        env_name = bc.get(key)
        if env_name and os.environ.get(str(env_name)):
            return True
    return False


_ENGINE_MAP: Dict[str, Type[BaseProvider]] = {
    "ollama": OllamaProvider,
    "llamacpp": LlamaCPPProvider,
    "colab": ColabWorkerProvider,
    "vertex": VertexAIProvider,
}


class GoogleCloudSelfhostedProvider(BaseProvider):
    """Single provider that aggregates all GCP-hosted inference backends."""

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        raw_backends: List[Dict[str, Any]] = list(
            self.config.get("backends", [])
        )
        self._backends: List[BaseProvider] = self._init_backends(raw_backends)
        if not self._backends:
            logger.warning(
                "google_cloud_selfhosted_no_backends",
                provider=self.provider_id,
                hint="Set at least one backend endpoint env var",
            )

    def _init_backends(
        self, backend_configs: List[Dict[str, Any]]
    ) -> List[BaseProvider]:
        ordered = sorted(
            backend_configs, key=lambda bc: int(bc.get("priority", 99))
        )
        backends: List[BaseProvider] = []
        for bc in ordered:
            engine = bc.get("engine", "")
            cls = _ENGINE_MAP.get(engine)
            if cls is None:
                logger.warning("gcs_unknown_engine", engine=engine)
                continue
            
            sub_id = f"{self.provider_id}.{engine}"
            try:
                backend = cls(sub_id, dict(bc))
                # Rely on individual provider's knowledge of its own configuration requirements
                if not backend.is_available():
                    logger.debug("gcs_backend_skipped_unconfigured", engine=engine)
                    continue
                backends.append(backend)
                logger.debug(
                    "gcs_backend_registered", engine=engine, sub_id=sub_id
                )
            except Exception as exc:
                logger.warning(
                    "gcs_backend_init_failed", engine=engine, error=str(exc)
                )
        return backends

    def _pick_model(self, model: Optional[str], backend: BaseProvider) -> str:
        return model or backend.default_model or ""

    def warmup_targets(self) -> list[tuple[str, BaseProvider]]:
        return [(backend.provider_id, backend) for backend in self._backends]

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
        if not self._backends:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model or "",
                error="google_cloud_selfhosted: no backends configured",
            )

        last_error: str = "all backends failed"
        for backend in self._backends:
            if not backend.is_available():
                logger.debug(
                    "gcs_backend_unavailable", sub=backend.provider_id
                )
                continue
            resolved_model = self._pick_model(model, backend)
            try:
                result = await backend.invoke(
                    messages,
                    resolved_model,
                    stream=stream,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    prompt=prompt,
                    **kwargs,
                )
                if result.ok:
                    result.provider = self.provider_id
                    self.record_success()
                    return result
                last_error = result.error or "backend returned ok=False"
                logger.warning(
                    "gcs_backend_invoke_failed",
                    sub=backend.provider_id,
                    error=last_error,
                )
            except Exception as exc:
                last_error = str(exc) or type(exc).__name__
                self.record_failure(last_error)
                logger.warning(
                    "gcs_backend_exception",
                    sub=backend.provider_id,
                    error=last_error,
                )

        return ProviderResult(
            ok=False,
            provider=self.provider_id,
            model=model or "",
            error=last_error,
            error_category=classify_provider_error(last_error).value,
        )

    async def stream(  # type: ignore[override]
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self._backends:
            yield {"error": "google_cloud_selfhosted: no backends configured"}
            return

        for backend in self._backends:
            if not backend.is_available():
                continue
            resolved_model = self._pick_model(model, backend)
            yielded = False
            try:
                async for chunk in backend.stream(
                    messages,
                    resolved_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    prompt=prompt,
                    **kwargs,
                ):
                    yielded = True
                    yield chunk
                self.record_success()
                return
            except Exception as exc:
                backend.record_failure(str(exc))
                logger.warning(
                    "gcs_backend_stream_error",
                    sub=backend.provider_id,
                    error=str(exc),
                )
                if yielded:
                    return  # partial stream already sent; cannot switch
                continue

        yield {"error": "google_cloud_selfhosted: all backends unavailable"}

    async def health_check(self) -> ProviderHealth:
        if not self._backends:
            return ProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                error="no backends configured",
            )

        t0 = time.perf_counter()
        results: List[ProviderHealth] = list(
            await asyncio.gather(
                *[b.health_check() for b in self._backends],
                return_exceptions=False,
            )
        )
        latency = (time.perf_counter() - t0) * 1000

        healthy_count = sum(1 for r in results if r.healthy)
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=healthy_count > 0,
            latency_ms=latency,
            error=(
                None
                if healthy_count > 0
                else f"all {len(self._backends)} backends unhealthy"
            ),
        )
