"""
Pydantic schema for config/providers.toml — the SINGLE source of truth.

Every consumer (dispatcher, budget, monitoring, frontend) MUST load & validate
through this schema so that field types / defaults / constraints are enforced
at startup instead of silently drifting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Leaf helpers ──────────────────────────────────────────────────────────────


class ScoringWeights(BaseModel):
    latency: float = 0.4
    cost: float = 0.3
    reliability: float = 0.2
    bandwidth: float = 0.1


class ChainOfThoughtSuppression(BaseModel):
    suppress_for: List[str] = ["summary", "code"]
    force_for: List[str] = ["reasoning"]


class CostOptimization(BaseModel):
    max_budget_per_hour: float = 10.0
    preferred_providers_under_budget: List[str] = [
        "groq", "siliconeflow", "azure", "deepseek", "openai"
    ]


class Health(BaseModel):
    health_check_interval: int = 60
    timeout_seconds: int = 10
    retry_attempts: int = 3


class Raptor(BaseModel):
    level: str = "INFO"
    file: str = "logs/raptor.log"
    enable_cpu: bool = True
    enable_memory: bool = True
    sample_rate_ms: int = 200
    trace_exceptions: bool = True
    enable_dev_flags: bool = False


class Default(BaseModel):
    timeout_ms: int = 12000
    scoring_weights: ScoringWeights = ScoringWeights()
    chain_of_thought_suppression: ChainOfThoughtSuppression = (
        ChainOfThoughtSuppression()
    )
    cost_optimization: CostOptimization = CostOptimization()
    health: Health = Health()
    raptor: Raptor = Raptor()


class LoadBalancingHealthChecks(BaseModel):
    ollama_health: str = "/api/tags"
    router_health: str = "/health"
    timeout_seconds: int = 10


class LoadBalancingServerPriorities(BaseModel):
    primary_ollama: str = "192.175.23.150:8002"
    backup_router: str = "45.61.51.220:8000"


class LoadBalancing(BaseModel):
    enabled: bool = True
    strategy: str = "round_robin"
    health_check_interval: int = 30
    failure_threshold: int = 3
    recovery_threshold: int = 2
    failover_to_backup: bool = True
    max_failover_time: int = 60
    circuit_breaker_enabled: bool = True
    health_checks: LoadBalancingHealthChecks = LoadBalancingHealthChecks()
    server_priorities: LoadBalancingServerPriorities = (
        LoadBalancingServerPriorities()
    )


class ProviderConfig(BaseModel):
    """Schema for a single [providers.*] entry."""

    name: str
    endpoint: str = ""
    endpoint_env: Optional[str] = None
    endpoint_fallback: Optional[str] = None
    invoke_path: str = "/chat/completions"
    api_key_env: Optional[str] = None
    default_model: str = ""
    default_deployment: Optional[str] = None
    models: List[str] = []
    capabilities: List[str] = ["chat"]
    priority_tier: int = 50
    cost_score: float = 0.5
    cost_input_per1k: float = 0.0
    cost_output_per1k: float = 0.0
    default_timeout_ms: int = 12000
    bandwidth_score: float = 0.5
    rate_limit_per_min: int = 60
    supports_cot: bool = True
    cot_suppression_prompt: str = "Be concise."
    supports_openai_tools: Optional[bool] = None
    requires_env: Optional[List[str]] = None
    project_env: Optional[str] = None
    tier: str = "cloud"
    local_routing: bool = False
    is_active: bool = True
    display_name: Optional[str] = None
    selectable_requires_env: bool = False
    force_fallback: bool = False
    hidden: bool = False

    @property
    def resolved_display_name(self) -> str:
        return self.display_name or self.name


class ModelAlias(BaseModel):
    provider: str
    model: str


class ModelDefaults(BaseModel):
    provider: str = ""
    max_tokens: int = 4000
    temperature: float = 0.7
    supports_streaming: bool = True


# ── Root ──────────────────────────────────────────────────────────────────────


class ProviderToml(BaseModel):
    """Validated representation of the entire config/providers.toml file."""

    default: Default = Default()
    load_balancing: LoadBalancing = LoadBalancing()
    provider_aliases: Dict[str, str] = {}
    model_aliases: Dict[str, ModelAlias] = {}
    visible_providers: List[str] = []
    model_context_windows: Dict[str, int] = {}
    providers: Dict[str, ProviderConfig] = {}
    model_defaults: Dict[str, ModelDefaults] = {}

    @classmethod
    def load(cls, path: str | Path) -> "ProviderToml":
        """Parse & validate a providers.toml file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Provider config not found: {config_path}")

        try:
            import tomllib

            with open(config_path, "rb") as f:
                raw: dict = tomllib.load(f)
        except ImportError:
            import tomllib  # Python 3.11+

            with open(config_path, "rb") as f:
                raw = tomllib.load(f)

        return cls._from_raw(raw)

    @classmethod
    def _from_raw(cls, raw: dict) -> "ProviderToml":
        """Convert raw parsed TOML dict into validated model."""
        # Flatten nested sections
        defaults_raw = raw.get("default", {})
        if isinstance(defaults_raw, dict):
            for key in ("scoring_weights", "chain_of_thought_suppression",
                        "cost_optimization", "health", "raptor"):
                if key in raw:
                    defaults_raw[key] = raw[key]

        providers_raw = raw.get("providers", {})
        if not isinstance(providers_raw, dict):
            providers_raw = {}

        model_defaults_raw = raw.get("model_defaults", {})
        if not isinstance(model_defaults_raw, dict):
            model_defaults_raw = {}

        return cls(
            default=defaults_raw,
            load_balancing=raw.get("load_balancing", {}),
            provider_aliases=raw.get("provider_aliases", {}),
            model_aliases={
                k: v for k, v in raw.get("model_aliases", {}).items()
                if isinstance(v, dict)
            },
            visible_providers=raw.get("visible_providers", []),
            model_context_windows={
                k: int(v) for k, v in raw.get("model_context_windows", {}).items()
                if isinstance(v, (int, float))
            },
            providers=providers_raw,
            model_defaults=model_defaults_raw,
        )

    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        """Resolve a provider ID (possibly an alias) to its config."""
        canonical = self.provider_aliases.get(provider_id, provider_id)
        return self.providers.get(canonical)

    def resolve_model_alias(
        self, model: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve a short model name → (canonical_provider_id, canonical_model)."""
        alias = self.model_aliases.get(model)
        if alias is None:
            return None, None
        return alias.provider, alias.model

    def get_model_defaults(self, model: str) -> ModelDefaults:
        return self.model_defaults.get(model, ModelDefaults())

    def get_context_window(self, model: str, fallback: int = 8000) -> int:
        return self.model_context_windows.get(model, fallback)

    def as_json_serializable(self) -> dict:
        """Return a plain dict suitable for JSON serialization (→ providers.json)."""
        providers_out: dict[str, dict] = {}
        for pid, cfg in self.providers.items():
            entry = {
                "endpoint": cfg.endpoint,
                "endpoint_env": cfg.endpoint_env,
                "endpoint_fallback": cfg.endpoint_fallback,
                "api_key_env": cfg.api_key_env,
                "priority_tier": cfg.priority_tier,
                "capabilities": cfg.capabilities,
                "models": cfg.models,
                "cost_score": cfg.cost_score,
                "default_timeout_ms": cfg.default_timeout_ms,
                "rate_limit_per_min": cfg.rate_limit_per_min,
                "display_name": cfg.resolved_display_name,
                "is_active": cfg.is_active,
                "invoke_path": cfg.invoke_path if cfg.invoke_path != "/chat/completions" else None,
            }
            # Strip None values for JSON cleanliness
            entry = {k: v for k, v in entry.items() if v is not None}
            providers_out[pid] = entry

        return {
            "version": 2,
            "default_timeout_ms": self.default.timeout_ms,
            "providers": providers_out,
        }


# ── Convenience loader ────────────────────────────────────────────────────────

_CONFIG_CACHE: Optional[ProviderToml] = None


def load_provider_config(
    path: str | Path | None = None,
    use_cache: bool = True,
) -> ProviderToml:
    """Load, validate & cache the canonical provider config."""
    global _CONFIG_CACHE
    if use_cache and _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    if path is None:
        path = Path(__file__).resolve().parents[3] / "config" / "providers.toml"

    cfg = ProviderToml.load(path)
    if use_cache:
        _CONFIG_CACHE = cfg
    return cfg


def invalidate_cache() -> None:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None