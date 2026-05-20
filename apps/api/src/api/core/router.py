"""
Model Routing Core Logic

Intelligent routing for selecting and invoking AI models based on task type and context.
Supports multi-provider model selection with fallback chains and authorization headers.
"""

from typing import Dict, Any, Optional
import os
import httpx
from dataclasses import dataclass

# Tasks suitable for specialized Raptor model
RAPTOR_TASKS = {"summarize_trace", "quick_fix", "unit_test_hint", "infer_function_name"}


@dataclass
class ModelRoute:
    """Configuration for routing to a specific model endpoint."""
    url: str
    api_key: Optional[str]
    model_name: str


class ModelRouter:
    """
    Intelligent model routing based on task complexity and availability.
    
    Routes tasks to specialized Raptor model for:
    - summarize_trace
    - quick_fix
    - unit_test_hint
    - infer_function_name
    
    Falls back to general-purpose model for other tasks.
    Configuration via environment variables:
    - RAPTOR_URL, RAPTOR_API_KEY
    - FALLBACK_MODEL_URL, FALLBACK_MODEL_KEY
    """

    @property
    def raptor_url(self) -> Optional[str]:
        """Raptor model endpoint URL from environment."""
        return os.getenv("RAPTOR_URL")

    @property
    def raptor_key(self) -> Optional[str]:
        """Raptor model API key from environment."""
        return os.getenv("RAPTOR_API_KEY")

    @property
    def fallback_url(self) -> Optional[str]:
        """Fallback model endpoint URL from environment."""
        return os.getenv("FALLBACK_MODEL_URL")

    @property
    def fallback_key(self) -> Optional[str]:
        """Fallback model API key from environment."""
        return os.getenv("FALLBACK_MODEL_KEY")

    def choose_model(self, task: str, context: Dict[str, Any]) -> ModelRoute:
        """
        Select the best model route for the given task.
        
        Routes RAPTOR_TASKS to specialized Raptor model if available,
        otherwise uses fallback model. Raises RuntimeError if no endpoints configured.
        
        Args:
            task: Task identifier (e.g., 'quick_fix', 'summarize_trace')
            context: Contextual data for the task (unused in routing decision)
            
        Returns:
            ModelRoute with endpoint, credentials, and model name
            
        Raises:
            RuntimeError: If no model endpoints are configured
        """
        if task in RAPTOR_TASKS and self.raptor_url:
            return ModelRoute(
                url=self.raptor_url, api_key=self.raptor_key, model_name="raptor"
            )
        if self.fallback_url:
            return ModelRoute(
                url=self.fallback_url, api_key=self.fallback_key, model_name="fallback"
            )
        raise RuntimeError("No model endpoints configured")

    async def call_model(
        self, route: ModelRoute, payload: Dict[str, Any], timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Invoke a model endpoint with the given payload.
        
        Builds authorization headers if API key is present.
        Raises httpx exceptions on network/HTTP errors.
        
        Args:
            route: ModelRoute with endpoint and credentials
            payload: Request body (JSON-serializable dict)
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            Parsed JSON response from model endpoint
            
        Raises:
            httpx.RequestError: On network or HTTP error
        """
        headers = {"Content-Type": "application/json"}
        if route.api_key:
            headers["Authorization"] = f"Bearer {route.api_key}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(route.url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
