from typing import Dict, Any, Optional
import os
import httpx
from dataclasses import dataclass

RAPTOR_TASKS = {"summarize_trace", "quick_fix", "unit_test_hint", "infer_function_name"}


@dataclass
class ModelRoute:
    url: str
    api_key: Optional[str]
    model_name: str


class ModelRouter:
    @property
    def raptor_url(self) -> Optional[str]:
        return os.getenv("RAPTOR_URL")

    @property
    def raptor_key(self) -> Optional[str]:
        return os.getenv("RAPTOR_API_KEY")

    @property
    def fallback_url(self) -> Optional[str]:
        return os.getenv("FALLBACK_MODEL_URL")

    @property
    def fallback_key(self) -> Optional[str]:
        return os.getenv("FALLBACK_MODEL_KEY")

    def choose_model(self, task: str, context: Dict[str, Any]) -> ModelRoute:
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
        headers = {"Content-Type": "application/json"}
        if route.api_key:
            headers["Authorization"] = f"Bearer {route.api_key}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(route.url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
