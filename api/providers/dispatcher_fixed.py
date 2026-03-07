"""
Provider dispatcher that routes requests to appropriate provider implementations.

Updated: 2026-03-05
- Removed dead GCP providers (VMs terminated since 2026-01-11)
- Removed dead Kamatera providers (unreachable since 2026-01-11)
- Active providers: Groq, SiliconeFlow, Azure, DeepSeek, OpenAI, Anthropic, Gemini
"""

import os
import logging
import importlib
import inspect
from typing import Dict, Any, Optional
from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .ollama import OllamaProvider
from .llama_cpp import LlamaCPPProvider
from .groq import GroqProvider
from .gemini import GeminiProvider
from .siliconeflow import SiliconeFlowProvider
from .azure_openai import AzureOpenAIProvider
from .vertex_ai import VertexAIProvider
from .aliyun import AliyunProvider
from .generic import GenericProvider
from .mock_provider import MockProvider

# Import smart router (optional - graceful fallback if not available)
SMART_ROUTING_AVAILABLE = False
_smart_router_obj: Any = None
_health_monitor_obj: Any = None
try:
    smart_router_module = importlib.import_module("api.services.smart_router")
    provider_health_module = importlib.import_module("api.services.provider_health")
    _smart_router_obj = getattr(smart_router_module, "smart_router")
    _health_monitor_obj = getattr(provider_health_module, "health_monitor")
    SMART_ROUTING_AVAILABLE = _smart_router_obj is not None
except (ImportError, AttributeError):
    pass

logger = logging.getLogger(__name__)

CHAT_COMPLETIONS_PATH = "/v1/chat/completions"

# Load environment variables
try:
    from dotenv import load_dotenv

    # Load from multiple potential locations
    load_dotenv()  # .env
    load_dotenv(".env.local")  # .env.local
except ImportError:
    pass


class ProviderDispatcher:
    """Routes provider requests to appropriate provider implementations."""

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._provider_configs = self._load_provider_configs()

    def _load_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load provider configurations from TOML file."""
        try:
            try:
                import tomllib

                config_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "config", "providers.toml"
                )
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                    return config.get("providers", {})
            except ImportError:
                toml_module = importlib.import_module("toml")
                config_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "config", "providers.toml"
                )
                with open(config_path, "r", encoding="utf-8") as f:
                    config = toml_module.load(f)
                    return config.get("providers", {})
        except (ImportError, OSError, ValueError, TypeError) as e:
            print(f"Warning: Could not load provider config: {e}")
            return self._get_basic_providers()

    def _get_basic_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get basic provider configurations for development/testing."""
        return {
            "openai": {
                "endpoint": "https://api.openai.com",
                "api_key_env": "OPENAI_API_KEY",
                "invoke_path": CHAT_COMPLETIONS_PATH,
                "default_model": "gpt-4o-mini",
            },
            "anthropic": {
                "endpoint": "https://api.anthropic.com",
                "api_key_env": "ANTHROPIC_API_KEY",
                "invoke_path": "/v1/messages",
                "default_model": "claude-3-5-haiku-latest",
            },
            "ollama": {
                "endpoint": "http://localhost:11434",
                "invoke_path": "/api/generate",
            },
            "deepseek": {
                "endpoint": "https://api.deepseek.com",
                "api_key_env": "DEEPSEEK_API_KEY",
                "invoke_path": CHAT_COMPLETIONS_PATH,
                "default_model": "deepseek-chat",
            },
            "groq": {
                "endpoint": "https://api.groq.com/openai/v1",
                "api_key_env": "GROQ_API_KEY",
                "invoke_path": "/chat/completions",
                "default_model": "llama-3.1-8b-instant",
            },
            "gemini": {
                "endpoint": "https://generativelanguage.googleapis.com",
                "api_key_env": "GOOGLE_AI_API_KEY",
                "default_model": "gemini-2.0-flash",
            },
            "siliconeflow": {
                "endpoint": "https://api.siliconflow.com",
                "api_key_env": "SILICONEFLOW_API_KEY",
                "invoke_path": CHAT_COMPLETIONS_PATH,
                "default_model": "Qwen/Qwen2.5-7B-Instruct",
            },
            "azure": {
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://goblinos-resource.services.ai.azure.com"),
                "api_key_env": "AZURE_API_KEY",
                "default_model": "gpt-4o-mini",
                "api_version": os.getenv("AZURE_API_VERSION", "2024-05-01-preview"),
                "default_deployment": os.getenv("AZURE_DEPLOYMENT_ID", "gpt-4o-mini"),
            },
            "vertex_ai": {
                "endpoint": f"https://{os.getenv('GCP_REGION', 'us-central1')}-aiplatform.googleapis.com",
                "api_key_env": "GCP_ACCESS_TOKEN",
                "default_model": "gemini-2.0-flash",
                "project_id": os.getenv("GCP_PROJECT_ID", ""),
                "region": os.getenv("GCP_REGION", "us-central1"),
            },
            "aliyun": {
                "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                "api_key_env": "DASHSCOPE_API_KEY",
                "invoke_path": CHAT_COMPLETIONS_PATH,
                "default_model": "qwen-turbo",
            },
        }

    def _get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """Get provider configuration."""
        return self._provider_configs.get(provider_id, {})

    @staticmethod
    def _endpoint_matches(endpoint: str, *patterns: str) -> bool:
        return any(pattern in endpoint for pattern in patterns)

    def _create_provider_for_exact_id(
        self, provider_id: str, config: Dict[str, Any]
    ) -> Optional[BaseProvider]:
        if provider_id == "mock":
            return MockProvider({"default_model": "mock-gpt"})

        if provider_id == "openai":
            return OpenAIProvider.from_config(config)
        if provider_id == "anthropic":
            return AnthropicProvider.from_config(config)
        if provider_id == "ollama":
            return OllamaProvider.from_config(config)
        if provider_id == "llamacpp":
            return LlamaCPPProvider.from_config(config)
        if provider_id == "groq":
            return GroqProvider.from_config(config)
        if provider_id in ["gemini", "google"]:
            return GeminiProvider.from_config(config)
        if provider_id == "siliconeflow":
            return SiliconeFlowProvider.from_config(config)
        if provider_id == "aliyun":
            return AliyunProvider(config)
        if provider_id == "vertex_ai":
            return VertexAIProvider(config)
        if provider_id == "azure":
            return AzureOpenAIProvider(config)
        if provider_id in ["deepseek", "together", "replicate", "huggingface", "cohere"]:
            # These providers use OpenAI-compatible APIs.
            return OpenAIProvider.from_config(config)

        return None

    def _create_provider_for_endpoint(
        self, endpoint: str, config: Dict[str, Any]
    ) -> Optional[BaseProvider]:
        if self._endpoint_matches(endpoint, "openai.com"):
            return OpenAIProvider.from_config(config)
        if self._endpoint_matches(endpoint, "anthropic.com"):
            return AnthropicProvider.from_config(config)
        if self._endpoint_matches(endpoint, "localhost:11434"):
            return OllamaProvider.from_config(config)
        if self._endpoint_matches(endpoint, "127.0.0.1:8080", "ngrok.io"):
            return LlamaCPPProvider.from_config(config)
        if self._endpoint_matches(endpoint, "groq.com"):
            return GroqProvider.from_config(config)
        if self._endpoint_matches(endpoint, "generativelanguage.googleapis.com"):
            return GeminiProvider.from_config(config)
        if self._endpoint_matches(endpoint, "siliconflow.com"):
            return SiliconeFlowProvider.from_config(config)
        if self._endpoint_matches(endpoint, "services.ai.azure.com"):
            return AzureOpenAIProvider(config)
        if self._endpoint_matches(endpoint, "aiplatform.googleapis.com"):
            return VertexAIProvider(config)
        if self._endpoint_matches(endpoint, "dashscope.aliyuncs.com"):
            return AliyunProvider(config)

        return None

    def _create_provider(
        self, provider_id: str, config: Dict[str, Any]
    ) -> BaseProvider:
        """Create provider instance based on provider ID."""
        endpoint = config.get("endpoint", "")

        exact_provider = self._create_provider_for_exact_id(provider_id, config)
        if exact_provider is not None:
            return exact_provider

        endpoint_provider = self._create_provider_for_endpoint(endpoint, config)
        if endpoint_provider is not None:
            return endpoint_provider

        # Generic provider for custom endpoints
        return GenericProvider.from_config(config)

    async def _select_provider_via_smart_router(
        self, messages: Optional[list[Any]]
    ) -> Optional[str]:
        if not SMART_ROUTING_AVAILABLE or _smart_router_obj is None:
            return None

        try:
            selection_result = _smart_router_obj.select_provider(messages=messages or [])
            if inspect.isawaitable(selection_result):
                selection = await selection_result
            else:
                selection = selection_result
            logger.info(
                "Smart router selected: %s (%s)",
                selection.provider_id,
                selection.reason,
            )
            return selection.provider_id
        except (AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.warning("Smart router failed, falling back to basic selection: %s", e)
            return None

    @staticmethod
    def _is_provider_healthy(provider_id: str) -> bool:
        if SMART_ROUTING_AVAILABLE and _health_monitor_obj is not None:
            return bool(_health_monitor_obj.is_available(provider_id))
        return True

    @staticmethod
    def _is_provider_configured(
        config: Dict[str, Any], env_var: Optional[str], is_local: bool
    ) -> bool:
        if env_var is None:
            return True

        env_value = os.getenv(env_var, "")
        if env_value:
            return True

        if is_local and env_var.endswith("_URL"):
            endpoint = config.get("endpoint", "")
            return bool(endpoint and endpoint != "http://localhost:11434")

        return False

    def get_provider(self, provider_id: str) -> BaseProvider:
        """Get or create a provider instance."""
        if provider_id not in self._providers:
            config = self._get_provider_config(provider_id)
            self._providers[provider_id] = self._create_provider(provider_id, config)
        return self._providers[provider_id]

    async def _auto_select_provider(self, messages: Optional[list[Any]] = None) -> str:
        """
        Auto-select the best available provider.

        Updated priority order (2026-03-05):
        1. Groq (very cheap, fast)
        2. SiliconeFlow (cheap)
        3. Azure OpenAI (mid-tier)
        4. DeepSeek (good for code)
        5. OpenAI (quality fallback)
        6. Anthropic (premium fallback)

        Removed/Disabled:
        - GCP servers (VMs terminated since 2026-01-11)
        - Kamatera servers (unreachable since 2026-01-11)
        """
        smart_router_selection = await self._select_provider_via_smart_router(messages)
        if smart_router_selection:
            return smart_router_selection

        # Updated priority order: Cost-optimized, healthy providers first
        priority_providers = [
            # Tier 1: Very cheap cloud
            ("groq", "GROQ_API_KEY", False),  # Fast + cheap
            ("siliconeflow", "SILICONEFLOW_API_KEY", False),
            ("azure", "AZURE_API_KEY", False),  # Azure OpenAI
            # Tier 2: Budget cloud
            ("deepseek", "DEEPSEEK_API_KEY", False),  # Good for code
            # Tier 3: Standard cloud
            ("openai", "OPENAI_API_KEY", False),
            ("anthropic", "ANTHROPIC_API_KEY", False),
            ("gemini", "GOOGLE_AI_API_KEY", False),
            ("vertex_ai", "GCP_ACCESS_TOKEN", False),
            ("aliyun", "DASHSCOPE_API_KEY", False),
            # Tier 4: Local fallback
            ("ollama", None, True),  # Local Ollama
            # DISABLED: Dead Kamatera servers (unreachable since 2026-01-11)
            # ("llamacpp_kamatera", "LOCAL_LLM_API_KEY", True),
            # ("ollama_kamatera", "LOCAL_LLM_API_KEY", True),
        ]

        for provider_id, env_var, is_local in priority_providers:
            config = self._get_provider_config(provider_id)
            if not config:
                continue

            if not self._is_provider_healthy(provider_id):
                logger.debug("Skipping %s: unhealthy", provider_id)
                continue

            if not self._is_provider_configured(config, env_var, is_local):
                continue

            if env_var is None:
                logger.info("Auto-selected provider: %s (no key required)", provider_id)
            elif os.getenv(env_var, ""):
                logger.info(
                    "Auto-selected provider: %s (configured via %s)",
                    provider_id,
                    env_var,
                )
            else:
                logger.info(
                    "Auto-selected provider: %s (local endpoint configured)",
                    provider_id,
                )
            return provider_id

        # Fallback to mock for development stability if nothing else works
        logger.warning("No providers available, falling back to mock")
        return "mock"

    async def _resolve_provider_id(self, provider_id: Optional[str], messages: list[Any]) -> str:
        if provider_id is not None and provider_id != "auto":
            return provider_id

        resolved_provider = await self._auto_select_provider(messages)
        logger.info("Auto-selected provider: %s", resolved_provider)
        return resolved_provider

    @staticmethod
    def _extract_prompt(payload: Dict[str, Any]) -> str:
        messages = payload.get("messages", [])
        if "messages" in payload:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    return msg.get("content", "")
        return payload.get("prompt", "")

    @staticmethod
    def _build_invoke_kwargs(
        prompt: str, stream: bool, timeout_ms: int, model: Optional[str]
    ) -> Dict[str, Any]:
        invoke_kwargs: Dict[str, Any] = {
            "prompt": prompt,
            "stream": stream,
            "timeout_ms": timeout_ms,
        }
        if model is not None:
            invoke_kwargs["model"] = model
        return invoke_kwargs

    @staticmethod
    def _build_invoke_error(error_code: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": error_code,
            "latency_ms": 0,
        }

    @staticmethod
    def _format_provider_result(
        result: Any, stream: bool, provider_id: Optional[str], model: Optional[str]
    ) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return ProviderDispatcher._build_invoke_error("invalid-provider-response")

        if not result.get("ok", False):
            return result

        if stream:
            return {
                "ok": True,
                "stream": result.get("stream"),
                "latency_ms": result.get("latency_ms", 0),
            }

        result.setdefault("provider", provider_id)
        result.setdefault("model", model)
        return result

    async def invoke_provider(
        self,
        provider_id: Optional[str],
        model: Optional[str],
        payload: Dict[str, Any],
        timeout_ms: int,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Invoke a provider with the given parameters.

        Updated (2026-01-11):
        - Uses smart router for provider selection when provider_id is None
        - Supports automatic fallback on provider failure
        - Integrates with health monitoring
        """
        messages = payload.get("messages", [])
        resolved_provider_id: str = await self._resolve_provider_id(provider_id, messages)

        config = self._get_provider_config(resolved_provider_id)
        if not config:
            return self._build_invoke_error(f"unknown-provider:{resolved_provider_id}")

        # If model is not provided, use the default model for this provider
        if model is None:
            model = config.get("default_model")
            # If still None, let the provider implementation decide its own default

        provider = self.get_provider(resolved_provider_id)

        prompt = self._extract_prompt(payload)

        if not prompt and "messages" not in payload:
            return self._build_invoke_error("no-prompt-provided")

        # Invoke the provider - NO MOCK FALLBACK
        try:
            # Remove model from payload to avoid duplicate keyword argument
            invoke_payload = payload.copy()
            invoke_payload.pop("model", None)

            invoke_kwargs = self._build_invoke_kwargs(prompt, stream, timeout_ms, model)

            provider_impl: Any = provider
            result = await provider_impl.invoke(
                **invoke_kwargs,
                **invoke_payload,
            )

            return self._format_provider_result(result, stream, resolved_provider_id, model)

        except (
            RuntimeError,
            ValueError,
            TypeError,
        ) as e:
            # Return the original error - NO MOCK FALLBACK
            return self._build_invoke_error(f"provider-invocation-error:{str(e)}")


# Global dispatcher instance
dispatcher = ProviderDispatcher()


async def invoke_provider(
    pid: str, model: str, payload: Dict[str, Any], timeout_ms: int, stream: bool = False
) -> Dict[str, Any]:
    """
    Legacy function that maintains compatibility with existing code.
    Routes to the new provider dispatcher.
    """
    return await dispatcher.invoke_provider(pid, model, payload, timeout_ms, stream)
