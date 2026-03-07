"""
Providers and Models endpoint
Extracts available models from configured providers
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from api.config.providers import DEFAULT_PROVIDERS

router = APIRouter(tags=["providers"])

@router.get("/providers/models")
async def get_provider_models() -> Dict[str, Any]:
    """Get models from all configured providers"""
    try:
        models = []
        providers_map = {}
        
        for provider_config in DEFAULT_PROVIDERS:
            if not provider_config.get("enabled", True):
                continue
                
            provider_name = provider_config.get("name", "unknown")
            provider_models = provider_config.get("models", [])
            
            providers_map[provider_name] = {
                "name": provider_name,
                "enabled": provider_config.get("enabled", True),
                "api_key": provider_config.get("api_key"),
                "base_url": provider_config.get("base_url"),
            }
            
            for model_name in provider_models:
                models.append({
                    "name": model_name,
                    "provider": provider_name,
                    "provider_id": provider_name,
                    "enabled": True,
                })
        
        return {
            "models": models,
            "providers": list(providers_map.values()),
            "source": "configured",
            "total_models": len(models),
            "total_providers": len(providers_map),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")
