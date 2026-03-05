"""
Provider dispatcher that routes requests to appropriate provider implementations.
"""

import sys
import os
from typing import Dict, Any
from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .ollama import OllamaProvider
from .llama_cpp import LlamaCPPProvider
from .groq import GroqProvider
from .gemini import GeminiProvider
from .generic import GenericProvider

# Add src directory to path for routing imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Import providers from routing system
try:
    from routing.router import PROVIDERS as ROUTING_PROVIDERS

    PROVIDERS_AVAILABLE = True
except ImportError:
    PROVIDERS_AVAILABLE = False
    ROUTING_PROVIDERS = {}


class ProviderDispatcher:
    """Routes provider requests to appropriate provider implementations."""

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}

    def get_provider(self, provider_id: str, config: Dict[str, Any]) -> BaseProvider:
        """Get or create a provider instance."""
        if provider_id not in self._providers:
            self._providers[provider_id] = self._create_provider(provider_id, config)
        return self._providers[provider_id]

    def _get_basic_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get basic provider configurations for development/testing."""
        return {
            "openai": {
                "endpoint": "https://api.openai.com",
                "api_key_env": "OPENAI_API_KEY",
                "invoke_path": "/v1/chat/completions",
            },
            "anthropic": {
                "endpoint": "https://api.anthropic.com",
                "api_key_env": "ANTHROPIC_API_KEY",
                "invoke_path": "/v1/messages",
            },
            "ollama": {
                "endpoint": "http://localhost:11434",
                "invoke_path": "/api/generate",
            },
            "llamacpp": {
                "endpoint": "http://45.61.51.220:8000",
                "api_key_env": "LLAMACPP_API_KEY",
                "invoke_path": "/v1/chat/completions",
            },
            "groq": {
                "endpoint": "https://api.groq.com",
                "api_key_env": "GROQ_API_KEY",
                "invoke_path": "/v1/chat/completions",
            },
            "gemini": {
                "endpoint": "https://generativelanguage.googleapis.com",
                "api_key_env": "GOOGLE_API_KEY",
            },
        }

    def _get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """Get provider configuration, preferring routing system over basic providers."""
        if not PROVIDERS_AVAILABLE or provider_id not in ROUTING_PROVIDERS:
            return self._get_basic_providers().get(provider_id, {})

        # Use routing system configuration
        config = ROUTING_PROVIDERS[provider_id].copy()

        # Normalize endpoint and invoke_path for provider compatibility
        endpoint = config.get("endpoint", "")

        # Handle special cases for endpoint normalization
        if provider_id == "openai" and endpoint.endswith("/v1"):
            config["endpoint"] = endpoint.rstrip("/v1").rstrip("/")
            config["invoke_path"] = "/v1/chat/completions"
        elif provider_id == "groq" and "/openai/v1" in endpoint:
            config["endpoint"] = endpoint.replace("/openai/v1", "")
            config["invoke_path"] = "/openai/v1/chat/completions"
        elif provider_id in [
            "deepseek",
            "together",
            "replicate",
            "huggingface",
            "cohere",
        ]:
            # These providers use OpenAI-compatible APIs
            if not endpoint.endswith("/v1"):
                config["invoke_path"] = "/v1/chat/completions"

        return config

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
        elif (
            provider_id == "ollama"
            or "localhost:11434" in endpoint
            or "45.61.51.220:8000" in endpoint  # Router for Ollama
        ):
            return OllamaProvider.from_config(config)
        elif (
            provider_id in ["llamacpp", "llamacpp_kamatera"]
            or "127.0.0.1:8080" in endpoint
            or "45.61.51.220:8000" in endpoint  # Router for Llama.cpp
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

        This replaces the monolithic invoke_provider_impl.py function.
        """
        config = self._get_provider_config(provider_id)
        if not config:
            return {
                "ok": False,
                "error": f"unknown-provider:{provider_id}",
                "latency_ms": 0,
            }

        provider = self.get_provider(provider_id, config)

        # Extract prompt from payload
        prompt = ""
        if "messages" in payload:
            # OpenAI-style messages
            for msg in payload["messages"]:
                if msg.get("role") == "user":
                    prompt = msg.get("content", "")
                    break
        else:
            prompt = payload.get("prompt", "")

        if not prompt:
            return {"ok": False, "error": "no-prompt-provided", "latency_ms": 0}

        # Invoke the provider
        try:
            result = await provider.invoke(
                prompt=prompt,
                stream=stream,
                model=model,
                timeout_ms=timeout_ms,
                **payload,
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
                        return result
                else:
                    # Error case
                    return result
            else:
                # Should not happen with current implementation
                return {
                    "ok": False,
                    "error": "invalid-provider-response",
                    "latency_ms": 0,
                }

        except Exception as e:
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