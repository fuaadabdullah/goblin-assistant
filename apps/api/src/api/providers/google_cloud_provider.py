"""Google Cloud vLLM provider.

Targets a vLLM server on a GCP VM via its OpenAI-compatible API.
No custom protocol — POST /v1/chat/completions exactly like OpenAI.

Extends OpenAICompatibleProvider to inherit streaming, error handling,
and health-check patterns, then adds:
  - embed()  for BGE-M3 and any other embedding model served by vLLM
  - rerank() for BGE Reranker (via vLLM's /v1/score endpoint)
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Union

import httpx
import structlog

from .base import ProviderHealth
from .openai_compatible import OpenAICompatibleProvider

logger = structlog.get_logger(__name__)

_DEFAULT_EMBED_MODEL = "bge-m3"
_DEFAULT_EMBED_PATH = "/v1/embeddings"
_DEFAULT_RERANK_PATH = "/v1/score"


class GoogleCloudProvider(OpenAICompatibleProvider):
    """vLLM-backed Google Cloud inference provider.

    Configured via ``GOOGLE_CLOUD_VLLM_ENDPOINT`` (required).
    Supports chat, streaming, embeddings, and reranking.
    """

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        ep_env = str(self.config.get("endpoint_env", "") or "").strip()
        resolved = os.getenv(ep_env, "").strip() if ep_env else ""
        self._base_url = resolved or self.endpoint
        self._embed_model = str(self.config.get("embed_model", _DEFAULT_EMBED_MODEL))
        self._rerank_model = str(self.config.get("rerank_model", "bge-reranker-v2-m3"))

    # ── Embeddings ──────────────────────────────────────────────────────────

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "",
        **kwargs: Any,
    ) -> Union[List[float], List[List[float]]]:
        """Embed text(s) via vLLM's /v1/embeddings (BGE-M3 by default)."""
        if not self._base_url:
            raise ValueError("google_cloud: endpoint not configured")
        embed_model = model or self._embed_model
        is_single = isinstance(texts, str)
        inputs: List[str] = [texts] if is_single else list(texts)

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self._base_url}{_DEFAULT_EMBED_PATH}",
                    headers=self._headers(),
                    json={"model": embed_model, "input": inputs},
                )
            resp.raise_for_status()
            data = resp.json()
            embeddings = [item["embedding"] for item in data.get("data", [])]
            logger.debug(
                "google_cloud_embed",
                model=embed_model,
                count=len(embeddings),
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
            return embeddings[0] if is_single else embeddings
        except Exception as exc:
            logger.warning(
                "google_cloud_embed_failed",
                model=embed_model,
                error=str(exc),
            )
            raise

    # ── Reranking ───────────────────────────────────────────────────────────

    async def rerank(
        self,
        query: str,
        documents: List[str],
        model: str = "",
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Score query-document pairs via vLLM's /v1/score (BGE Reranker).

        Returns list of {"index": int, "score": float} sorted by score desc.
        """
        if not self._base_url:
            raise ValueError("google_cloud: GOOGLE_CLOUD_VLLM_ENDPOINT not configured")
        rerank_model = model or self._rerank_model
        pairs = [[query, doc] for doc in documents]

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self._base_url}{_DEFAULT_RERANK_PATH}",
                    headers=self._headers(),
                    json={
                        "model": rerank_model,
                        "text_1": query,
                        "text_2": pairs,
                    },
                )
            resp.raise_for_status()
            data = resp.json()
            scores = data.get("data", [])
            results = [
                {"index": i, "score": float(item.get("score", 0.0))}
                for i, item in enumerate(scores)
            ]
            results.sort(key=lambda x: x["score"], reverse=True)
            if top_n is not None:
                results = results[:top_n]
            logger.debug(
                "google_cloud_rerank",
                model=rerank_model,
                docs=len(documents),
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
            return results
        except Exception as exc:
            logger.warning(
                "google_cloud_rerank_failed",
                model=rerank_model,
                error=str(exc),
            )
            raise

    # ── Capabilities ────────────────────────────────────────────────────────

    def capabilities(self) -> Any:
        caps = super().capabilities()
        caps["embeddings"] = True
        caps["reranking"] = True
        return caps

    # ── Health ──────────────────────────────────────────────────────────────

    async def health_check(self) -> ProviderHealth:
        if not self._base_url:
            return ProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                error="GOOGLE_CLOUD_VLLM_ENDPOINT not configured",
            )
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/models",
                    headers=self._headers(),
                )
            latency = (time.perf_counter() - t0) * 1000
            ok = resp.status_code < 400
            return ProviderHealth(
                provider_id=self.provider_id,
                healthy=ok,
                latency_ms=latency,
                error=(None if ok else f"HTTP {resp.status_code}"),
            )
        except (httpx.HTTPError, ValueError) as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                latency_ms=latency,
                error=str(exc),
            )
