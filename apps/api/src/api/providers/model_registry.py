"""ModelRegistry — model-first routing layer.

Separates *model definitions* from *provider implementations*.

The ProviderRegistry knows: which provider classes exist.
The ModelRegistry knows: which models are available and on which providers.

Usage
-----
>>> registry = ModelRegistry.from_dispatcher_configs(dispatcher._configs)
>>> backends = registry.backends_for("qwen3-32b")
[ModelBackend(provider_id="google_cloud",  model="qwen3-32b", priority=1),
 ModelBackend(provider_id="ollama_local",  model="qwen3:32b", priority=2)]
>>> registry.provider_for("qwen3-32b")  # first available
"google_cloud"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .dispatcher_pkg.config import normalize_token


@dataclass(frozen=True)
class ModelBackend:
    """One provider that can serve a given logical model name."""

    provider_id: str
    model: str
    priority: int = 50
    supports_embeddings: bool = False
    supports_reranking: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "priority": self.priority,
            "supports_embeddings": self.supports_embeddings,
            "supports_reranking": self.supports_reranking,
        }


class ModelRegistry:
    """Inverted index from logical model name → ordered list of backends.

    Built from provider configs at startup; cheap to rebuild on config reload.
    """

    def __init__(self) -> None:
        self._index: Dict[str, List[ModelBackend]] = {}

    # ── Construction ─────────────────────────────────────────────────────────

    @classmethod
    def from_dispatcher_configs(
        cls,
        configs: Dict[str, Dict[str, Any]],
    ) -> "ModelRegistry":
        """Build the registry by scanning all provider configs."""
        registry = cls()
        for provider_id, cfg in configs.items():
            if not cfg.get("is_active", True):
                continue
            priority = int(cfg.get("priority_tier", 50))
            supports_embed = bool(cfg.get("supports_embeddings", False))
            supports_rerank = bool(cfg.get("supports_reranking", False))
            caps = [c.lower() for c in cfg.get("capabilities", [])]
            if "embedding" in caps or "embeddings" in caps:
                supports_embed = True

            models: List[str] = list(cfg.get("models", []))
            if cfg.get("default_model"):
                dm = str(cfg["default_model"])
                if dm and dm not in models:
                    models.insert(0, dm)

            for model_name in models:
                if not model_name:
                    continue
                backend = ModelBackend(
                    provider_id=provider_id,
                    model=model_name,
                    priority=priority,
                    supports_embeddings=supports_embed,
                    supports_reranking=supports_rerank,
                )
                registry._add(model_name, backend)

            for bc in cfg.get("backends", []):
                sub_priority = int(bc.get("priority", priority))
                for bm in bc.get("models", []):
                    if not bm:
                        continue
                    backend = ModelBackend(
                        provider_id=provider_id,
                        model=bm,
                        priority=sub_priority,
                    )
                    registry._add(bm, backend)

        return registry

    def _add(self, model_name: str, backend: ModelBackend) -> None:
        key = _normalize(model_name)
        bucket = self._index.setdefault(key, [])
        if not any(
            b.provider_id == backend.provider_id and b.model == backend.model
            for b in bucket
        ):
            bucket.append(backend)
            bucket.sort(key=lambda b: b.priority)

    # ── Queries ──────────────────────────────────────────────────────────────

    def backends_for(
        self,
        model_name: str,
        *,
        require_embeddings: bool = False,
        require_reranking: bool = False,
    ) -> List[ModelBackend]:
        """Return all backends that can serve model_name, priority order."""
        key = _normalize(model_name)
        backends = list(self._index.get(key, []))
        if require_embeddings:
            backends = [b for b in backends if b.supports_embeddings]
        if require_reranking:
            backends = [b for b in backends if b.supports_reranking]
        return backends

    def provider_for(
        self,
        model_name: str,
        *,
        prefer_provider: Optional[str] = None,
        require_embeddings: bool = False,
    ) -> Optional[str]:
        """Return the highest-priority provider_id that can serve model_name.

        If prefer_provider is set and it exists in the backend list, it wins.
        """
        backends = self.backends_for(
            model_name, require_embeddings=require_embeddings
        )
        if not backends:
            return None
        if prefer_provider:
            for b in backends:
                if b.provider_id == prefer_provider:
                    return b.provider_id
        return backends[0].provider_id

    def all_models(self) -> List[str]:
        """Sorted list of all known logical model names."""
        return sorted(self._index.keys())

    def providers_for_model(self, model_name: str) -> List[str]:
        """Ordered list of provider_ids that can serve model_name."""
        return [b.provider_id for b in self.backends_for(model_name)]

    def model_catalog(self) -> Dict[str, List[Dict[str, Any]]]:
        """Full catalog: model_name → list of backend dicts."""
        return {
            name: [b.to_dict() for b in backends]
            for name, backends in sorted(self._index.items())
        }

    def embedding_providers(self) -> List[str]:
        """Unique provider_ids that support embeddings, priority order."""
        seen: set[str] = set()
        result: List[str] = []
        for backends in self._index.values():
            for b in backends:
                if b.supports_embeddings and b.provider_id not in seen:
                    seen.add(b.provider_id)
                    result.append(b.provider_id)
        return result

    def __len__(self) -> int:
        return len(self._index)

    def __repr__(self) -> str:
        return (
            f"ModelRegistry({len(self._index)} models, "
            f"{sum(len(v) for v in self._index.values())} backends)"
        )


def _supported_models_for_provider(cfg: Dict[str, Any]) -> set[str]:
    supported: set[str] = set()

    default_model = str(cfg.get("default_model", "")).strip()
    if default_model:
        supported.add(default_model)

    for model_name in cfg.get("models", []):
        model = str(model_name).strip()
        if model:
            supported.add(model)

    for backend in cfg.get("backends", []):
        if not isinstance(backend, dict):
            continue
        for model_name in backend.get("models", []):
            model = str(model_name).strip()
            if model:
                supported.add(model)

    return supported


def validate_model_alias_targets(
    *,
    provider_toml: Any,
    provider_configs: Dict[str, Dict[str, Any]],
    logger: Any,
) -> None:
    """Warn about model aliases that point to unknown providers or models."""
    if provider_toml is None:
        return

    provider_aliases = {
        normalize_token(alias): normalize_token(target)
        for alias, target in getattr(provider_toml, "provider_aliases", {}).items()
        if str(alias).strip() and str(target).strip()
    }

    for alias, alias_config in getattr(provider_toml, "model_aliases", {}).items():
        provider = normalize_token(str(getattr(alias_config, "provider", "") or ""))
        model = str(getattr(alias_config, "model", "") or "").strip()
        if not provider or not model:
            continue

        canonical_provider = provider_aliases.get(provider, provider)
        provider_cfg = provider_configs.get(canonical_provider)
        if provider_cfg is None:
            logger.warning(
                "model_alias_target_provider_missing",
                alias=alias,
                provider=canonical_provider,
                model=model,
            )
            continue

        supported_models = _supported_models_for_provider(provider_cfg)
        if model not in supported_models:
            logger.warning(
                "model_alias_target_model_missing",
                alias=alias,
                provider=canonical_provider,
                model=model,
                supported_models=sorted(supported_models),
            )


def _normalize(name: str) -> str:
    return name.strip().lower()


# ── Module-level singleton (lazy-built from dispatcher) ───────────────────

_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Return the module-level ModelRegistry, building it if needed."""
    global _registry
    if _registry is None:
        _registry = _build_from_dispatcher()
    return _registry


def invalidate_model_registry() -> None:
    """Force a rebuild on the next call to get_model_registry()."""
    global _registry
    _registry = None


def _build_from_dispatcher() -> ModelRegistry:
    from .dispatcher import dispatcher  # deferred — avoids circular import

    return ModelRegistry.from_dispatcher_configs(dispatcher._configs)
