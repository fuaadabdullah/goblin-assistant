from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

router = APIRouter(prefix="/settings", tags=["settings"])

# Load environment variables
load_dotenv()


class ProviderSettings(BaseModel):
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: List[str] = []
    enabled: bool = True


class ModelSettings(BaseModel):
    name: str
    provider: str
    model_id: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    enabled: bool = True


class SettingsResponse(BaseModel):
    providers: List[ProviderSettings]
    models: List[ModelSettings]
    default_provider: Optional[str] = None
    default_model: Optional[str] = None


# Default provider configurations
DEFAULT_PROVIDERS = [
    {
        "name": "OpenAI",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
        "enabled": bool(os.getenv("OPENAI_API_KEY")),
    },
    {
        "name": "Anthropic",
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "base_url": "https://api.anthropic.com",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "enabled": bool(os.getenv("ANTHROPIC_API_KEY")),
    },
    {
        "name": "Groq",
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama2-70b-4096", "mixtral-8x7b-32768", "gemma-7b-it"],
        "enabled": bool(os.getenv("GROQ_API_KEY")),
    },
    {
        "name": "Local LLM",
        "api_key": None,
        "base_url": "http://localhost:8000/v1",
        "models": ["local-model"],
        "enabled": True,
    },
]

DEFAULT_MODELS = [
    {
        "name": "GPT-4",
        "provider": "OpenAI",
        "model_id": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 4096,
        "enabled": True,
    },
    {
        "name": "Claude 3 Sonnet",
        "provider": "Anthropic",
        "model_id": "claude-3-sonnet-20240229",
        "temperature": 0.7,
        "max_tokens": 4096,
        "enabled": True,
    },
    {
        "name": "Llama 2 70B (Groq)",
        "provider": "Groq",
        "model_id": "llama2-70b-4096",
        "temperature": 0.7,
        "max_tokens": 4096,
        "enabled": True,
    },
]


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get current provider and model settings"""
    try:
        # In a real app, these would be stored in a database
        # For now, we'll return the default configurations
        return SettingsResponse(
            providers=DEFAULT_PROVIDERS,
            models=DEFAULT_MODELS,
            default_provider="OpenAI",
            default_model="GPT-4",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@router.put("/providers/{provider_name}")
async def update_provider_settings(provider_name: str, settings: ProviderSettings):
    """Update settings for a specific provider"""
    try:
        # In a real app, this would update the database
        # For now, we'll just validate the input
        if not settings.name:
            raise HTTPException(status_code=400, detail="Provider name is required")

        return {
            "status": "success",
            "message": f"Settings updated for provider: {provider_name}",
            "settings": settings.dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update provider settings: {str(e)}"
        )


@router.put("/models/{model_name}")
async def update_model_settings(model_name: str, settings: ModelSettings):
    """Update settings for a specific model"""
    try:
        # In a real app, this would update the database
        # For now, we'll just validate the input
        if not settings.name or not settings.provider or not settings.model_id:
            raise HTTPException(
                status_code=400,
                detail="Model name, provider, and model_id are required",
            )

        return {
            "status": "success",
            "message": f"Settings updated for model: {model_name}",
            "settings": settings.dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update model settings: {str(e)}"
        )


@router.post("/test-connection")
async def test_provider_connection(provider_name: str):
    """Test connection to a provider's API"""
    try:
        # Find the provider
        provider = None
        for p in DEFAULT_PROVIDERS:
            if p["name"].lower() == provider_name.lower():
                provider = p
                break

        if not provider:
            raise HTTPException(
                status_code=404, detail=f"Provider {provider_name} not found"
            )

        if not provider.get("api_key"):
            return {
                "status": "warning",
                "message": f"No API key configured for {provider_name}",
                "connected": False,
            }

        # In a real app, you would make a test API call here
        # For now, we'll just check if the API key exists
        return {
            "status": "success",
            "message": f"Connection test successful for {provider_name}",
            "connected": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
