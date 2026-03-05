"""
Provider dispatcher that routes requests to appropriate provider implementations.

Updated: 2026-01-11
- Integrated with smart router for intelligent provider selection
- Added health monitoring integration
- Removed dead Kamatera providers from priority list
- GCP providers now primary for cost optimization
"""

import os
import logging
from typing import Dict, Any
from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .ollama import OllamaProvider
from .llama_cpp import LlamaCPPProvider
from .kamatera_ollama import KamateraOllamaProvider
from .kamatera_llamacpp import KamateraLlamaCppProvider
from .groq import GroqProvider
from .gemini import GeminiProvider
from .siliconeflow import SiliconeFlowProvider
from .azure_openai import AzureOpenAIProvider
from .generic import GenericProvider
from .mock_provider import MockProvider

# Import smart router (optional - graceful fallback if not available)
try:
    from api.services.smart_router import smart_router, RoutingStrategy
    from api.services.provider_health import health_monitor

    SMART_ROUTING_AVAILABLE = True
except ImportError:
    SMART_ROUTING_AVAILABLE = False
    smart_router = None
    health_monitor = None

logger = logging.getLogger(__name__)

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
            import toml

            config_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "config", "providers.toml"
            )
            with open(config_path, "r") as f:
                config = toml.load(f)
                return config.get("providers", {})
        except Exception as e:
            print(f"Warning: Could not load provider config: {e}")
            return self._get_basic_providers()

    def _get_basic_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get basic provider configurations for development/testing."""
        return {
            "openai": {
                "endpoint": "https://api.openai.com",
                "api_key_env": "OPENAI_API_KEY",
                "invoke_path": "/v1/chat/completions",
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
            # GCP Ollama Server (replaces Kamatera)
            "ollama_gcp": {
                "endpoint": os.getenv("OLLAMA_GCP_URL", "http://localhost:11434"),
                "invoke_path": "/api/generate",
                "api_key_env": "LOCAL_LLM_API_KEY",
                "default_model": "qwen2.5:latest",
            },
            # GCP LlamaCPP Server (replaces Kamatera)
            "llamacpp_gcp": {
                "endpoint": os.getenv("LLAMACPP_GCP_URL", "http://localhost:8000"),
                "invoke_path": "/v1/chat/completions",
                "api_key_env": "LOCAL_LLM_API_KEY",
                "default_model": "qwen2.5-7b-instruct",
            },
            # Legacy Kamatera endpoints (deprecated - use GCP instead)
            "ollama_kamatera": {
                "endpoint": os.getenv(
                    "KAMATERA_SERVER2_URL", "http://192.175.23.150:8002"
                ),
                "invoke_path": "/api/generate",
                "api_key_env": "LOCAL_LLM_API_KEY",
            },
            "llamacpp_kamatera": {
                "endpoint": os.getenv(
                    "KAMATERA_SERVER1_URL", "http://45.61.51.220:8000"
                ),
                "invoke_path": "/v1/chat/completions",
                "api_key_env": "LOCAL_LLM_API_KEY",
                "default_model": "qwen2.5:latest",
            },
            "deepseek": {
                "endpoint": "https://api.deepseek.com",
                "api_key_env": "DEEPSEEK_API_KEY",
                "invoke_path": "/v1/chat/completions",
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
                "invoke_path": "/v1/chat/completions",
                "default_model": "Qwen/Qwen2.5-7B-Instruct",
            },
            "azure": {
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://goblinos-resource.services.ai.azure.com"),
                "api_key_env": "AZURE_API_KEY",
                "default_model": "gpt-4o-mini",
                "api_version": os.getenv("AZURE_API_VERSION", "2024-05-01-preview"),
                "default_deployment": os.getenv("AZURE_DEPLOYMENT_ID", "gpt-4o-mini"),
            },
        }

    def _get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """Get provider configuration."""
        return self._provider_configs.get(provider_id, {})

    def _create_provider(
        self, provider_id: str, config: Dict[str, Any]
    ) -> BaseProvider:
        """Create provider instance based on provider ID."""
        endpoint = config.get("endpoint", "")

        # Route based on provider ID or endpoint patterns
        if provider_id == "openai" or "openai.com" in endpoint:
            return OpenAIProvider.from_config(config)
        elif provider_id == "anthropic" or "anthropic.com" in endpoint:
            return AnthropicProvider.from_config(config)
        elif provider_id == "ollama_kamatera" or "192.175.23.150:8002" in endpoint:
            return KamateraOllamaProvider.from_config(config)
        elif provider_id == "llamacpp_kamatera" or "45.61.51.220:8000" in endpoint:
            return KamateraLlamaCppProvider.from_config(config)
        elif (
            provider_id in ["ollama", "ollama_gcp"]
            or "localhost:11434" in endpoint
            or "45.61.51.220:8002" in endpoint
            or "34.60.255.199:11434" in endpoint  # GCP Ollama
        ):
            return OllamaProvider.from_config(config)
        elif (
            provider_id in ["llamacpp", "llamacpp_kamatera", "llamacpp_gcp"]
            or "127.0.0.1:8080" in endpoint
            or "192.175.23.150:8000" in endpoint
            or "34.132.226.143:8000" in endpoint  # GCP LlamaCPP
            or "ngrok.io" in endpoint
        ):
            return LlamaCPPProvider.from_config(config)
        elif provider_id == "groq" or "groq.com" in endpoint:
            return GroqProvider.from_config(config)
        elif (
            provider_id in ["gemini", "google"]
            or "generativelanguage.googleapis.com" in endpoint
        ):
            return GeminiProvider.from_config(config)
        elif provider_id in ["siliconeflow", "aliyun"] or "siliconflow.com" in endpoint:
            return SiliconeFlowProvider.from_config(config)
        elif provider_id == "azure" or "services.ai.azure.com" in endpoint:
            return AzureOpenAIProvider(config)
        elif provider_id == "mock":
            return MockProvider({"default_model": "mock-gpt"})
        elif provider_id in [
            "deepseek",
            "together",
            "replicate",
            "huggingface",
            "cohere",
        ]:
            # These providers use OpenAI-compatible APIs, so use OpenAI provider
            return OpenAIProvider.from_config(config)
        else:
            # Generic provider for custom endpoints
            return GenericProvider.from_config(config)

    def get_provider(self, provider_id: str) -> BaseProvider:
        """Get or create a provider instance."""
        if provider_id not in self._providers:
            config = self._get_provider_config(provider_id)
            self._providers[provider_id] = self._create_provider(provider_id, config)
        return self._providers[provider_id]

    async def _auto_select_provider(self, messages: list = None) -> str:
        """
        Auto-select the best available provider.

        Updated priority order (2026-01-11):
        1. GCP Ollama (free, fast, healthy)
        2. GCP llama.cpp (free, healthy)
        3. Groq (very cheap, fast)
        4. SiliconeFlow (cheap)
        5. DeepSeek (good for code)
        6. OpenAI (quality fallback)
        7. Anthropic (premium fallback)

        Dead/Disabled:
        - Kamatera servers (unreachable since 2026-01-11)
        """
        # Use smart router if available
        if SMART_ROUTING_AVAILABLE and smart_router is not None:
            try:
                selection = await smart_router.select_provider(
                    messages=messages or [],
                )
                logger.info(
                    f"Smart router selected: {selection.provider_id} ({selection.reason})"
                )
                return selection.provider_id
            except Exception as e:
                logger.warning(
                    f"Smart router failed, falling back to basic selection: {e}"
                )

        # Updated priority order: Cost-optimized, healthy providers first
        priority_providers = [
            # Tier 0: Free/Local (GCP) — DISABLED: GCP VMs are currently unreachable
            # ("ollama_gcp", "OLLAMA_GCP_URL", True),
            # ("llamacpp_gcp", "LLAMACPP_GCP_URL", True),
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

            # Check health if smart routing is available
            if SMART_ROUTING_AVAILABLE and health_monitor is not None:
                if not health_monitor.is_available(provider_id):
                    logger.debug(f"Skipping {provider_id}: unhealthy")
                    continue

            # If no env_var required (local providers)
            if env_var is None:
                logger.info(f"Auto-selected provider: {provider_id} (no key required)")
                return provider_id

            # Check if env var is set
            env_value = os.getenv(env_var, "")
            if config and env_value:
                logger.info(
                    f"Auto-selected provider: {provider_id} (configured via {env_var})"
                )
                return provider_id

            # For local providers with optional env vars, check URL directly
            if is_local and env_var and env_var.endswith("_URL"):
                endpoint = config.get("endpoint", "")
                if (
                    endpoint and endpoint != "http://localhost:11434"
                ):  # Has custom endpoint
                    logger.info(
                        f"Auto-selected provider: {provider_id} (local endpoint configured)"
                    )
                    return provider_id

        # Fallback to mock for development stability if nothing else works
        logger.warning("No providers available, falling back to mock")
        return "mock"

    async def invoke_provider(
        self,
        provider_id: str,
        model: str,
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

        # Handle None or "auto" provider_id - use smart routing
        if provider_id is None or provider_id == "auto":
            provider_id = await self._auto_select_provider(messages)
            logger.info(f"Auto-selected provider: {provider_id}")

        config = self._get_provider_config(provider_id)
        if not config:
            return {
                "ok": False,
                "error": f"unknown-provider:{provider_id}",
                "latency_ms": 0,
            }

        # If model is not provided, use the default model for this provider
        if model is None:
            model = config.get("default_model")
            # If still None, let the provider implementation decide its own default

        provider = self.get_provider(provider_id)

        # Extract prompt from payload
        prompt = ""
        if "messages" in payload:
            # OpenAI-style messages - find the LAST user message as the active prompt
            for msg in reversed(payload["messages"]):
                if msg.get("role") == "user":
                    prompt = msg.get("content", "")
                    break

        # Fallback to prompt in payload if messages not found or no user message
        if not prompt:
            prompt = payload.get("prompt", "")

        if not prompt and "messages" not in payload:
            return {"ok": False, "error": "no-prompt-provided", "latency_ms": 0}

        # Invoke the provider - NO MOCK FALLBACK
        try:
            # Remove model from payload to avoid duplicate keyword argument
            invoke_payload = payload.copy()
            invoke_payload.pop("model", None)

            # Only pass model if we have one; otherwise let the provider use its default
            invoke_kwargs = {
                "prompt": prompt,
                "stream": stream,
                "timeout_ms": timeout_ms,
            }
            if model is not None:
                invoke_kwargs["model"] = model

            result = await provider.invoke(
                **invoke_kwargs,
                **invoke_payload,
            )

            # Handle streaming vs non-streaming results
            if isinstance(result, dict):
                if result.get("ok", False):
                    if stream:
                        # For streaming, return the stream generator
                        return {
                            "ok": True,
                            "stream": result.get("stream"),
                            "latency_ms": result.get("latency_ms", 0),
                        }
                    else:
                        # For non-streaming, return the result
                        result.setdefault("provider", provider_id)
                        result.setdefault("model", model)
                        return result
                else:
                    # Return the original error - NO MOCK FALLBACK
                    return result
            else:
                # Should not happen with current implementation
                return {
                    "ok": False,
                    "error": "invalid-provider-response",
                    "latency_ms": 0,
                }

        except Exception as e:
            # Return the original error - NO MOCK FALLBACK
            return {
                "ok": False,
                "error": f"provider-invocation-error:{str(e)}",
                "latency_ms": 0,
            }


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
