"""
Provider configuration settings for monitoring
"""

from typing import List, Dict, Any


# Default provider configurations
DEFAULT_PROVIDERS = [
    {
        "name": "openai",
        "api_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "enabled": True,
    },
    {
        "name": "anthropic",
        "api_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com",
        "models": ["claude-3-opus", "claude-3-sonnet"],
        "enabled": True,
    },
    {
        "name": "google",
        "api_key": "GOOGLE_AI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "models": ["gemini-pro", "gemini-pro-vision"],
        "enabled": True,
    },
    {
        "name": "deepseek",
        "api_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-coder"],
        "enabled": True,
    },
    {
        "name": "groq",
        "api_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.1-8b-instant"],
        "enabled": True,
    },
    {
        "name": "siliconeflow",
        "api_key": "SILICONEFLOW_API_KEY",
        "base_url": "https://api.siliconflow.com",
        "models": [
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-Coder-7B-Instruct",
            "deepseek-ai/DeepSeek-V2.5",
        ],
        "enabled": True,
    },
    {
        "name": "azure",
        "api_key": "AZURE_API_KEY",
        "base_url": "https://goblinos-resource.services.ai.azure.com",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "enabled": True,
    },
    {
        "name": "vertex_ai",
        "api_key": "GCP_ACCESS_TOKEN",
        "base_url": "https://us-central1-aiplatform.googleapis.com",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        "enabled": True,
    },
    {
        "name": "aliyun",
        "api_key": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
        "enabled": True,
    },
    {
        "name": "ollama_gcp",
        "api_key": None,
        "base_url": "http://34.60.255.199:11434",
        "models": ["qwen2.5:3b", "llama3.2:1b"],
        "enabled": False,
    },
    {
        "name": "llamacpp_gcp",
        "api_key": None,
        "base_url": "http://34.132.226.143:8000",
        "models": ["qwen2.5-3b-instruct-q4_k_m"],
        "enabled": False,
    },
]

# Default model configurations
DEFAULT_MODELS = {
    "gpt-4": {
        "provider": "openai",
        "max_tokens": 8000,
        "temperature": 0.7,
        "supports_streaming": True,
    },
    "gpt-3.5-turbo": {
        "provider": "openai",
        "max_tokens": 4000,
        "temperature": 0.7,
        "supports_streaming": True,
    },
    "claude-3-opus": {
        "provider": "anthropic",
        "max_tokens": 100000,
        "temperature": 0.7,
        "supports_streaming": True,
    },
    "qwen2.5:3b": {
        "provider": "ollama_gcp",
        "max_tokens": 4000,
        "temperature": 0.2,
        "supports_streaming": True,
    },
    "deepseek-chat": {
        "provider": "deepseek",
        "max_tokens": 4000,
        "temperature": 0.7,
        "supports_streaming": True,
    },
    "llama-3.1-8b-instant": {
        "provider": "groq",
        "max_tokens": 4000,
        "temperature": 0.7,
        "supports_streaming": True,
    },
    "gemini-2.0-flash-vertex": {
        "provider": "vertex_ai",
        "max_tokens": 8000,
        "temperature": 0.7,
        "supports_streaming": False,
    },
    "qwen-turbo": {
        "provider": "aliyun",
        "max_tokens": 4000,
        "temperature": 0.7,
        "supports_streaming": True,
    },
}


def get_provider_settings() -> List[Dict[str, Any]]:
    """Get provider settings for monitoring"""
    return DEFAULT_PROVIDERS


def get_provider_config() -> Dict[str, Any]:
    """Get overall provider configuration"""
    return {
        "health_check_interval": 60,
        "timeout": 10,
        "retry_attempts": 3,
    }


def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get configuration for a specific model"""
    return DEFAULT_MODELS.get(model_name, {})
