"""
System Configuration Module
Provides system-wide configuration settings and defaults
"""

import os
from typing import Dict, Any, Optional


def get_system_config() -> Dict[str, Any]:
    """Get system configuration with environment overrides"""
    return {
        "observability": {
            "log_decisions_to_file": os.getenv("LOG_DECISIONS_TO_FILE", "false").lower() == "true",
            "decision_log_file": os.getenv("DECISION_LOG_FILE", "decisions.log"),
            "enable_decision_caching": os.getenv("ENABLE_DECISION_CACHING", "true").lower() == "true",
            "decision_cache_size": int(os.getenv("DECISION_CACHE_SIZE", "1000"))
        },
        "memory": {
            "promotion_threshold": float(os.getenv("MEMORY_PROMOTION_THRESHOLD", "0.7")),
            "max_memory_items": int(os.getenv("MAX_MEMORY_ITEMS", "100")),
            "memory_retention_days": int(os.getenv("MEMORY_RETENTION_DAYS", "30"))
        },
        "retrieval": {
            "max_retrieval_results": int(os.getenv("MAX_RETRIEVAL_RESULTS", "10")),
            "retrieval_timeout_seconds": int(os.getenv("RETRIEVAL_TIMEOUT_SECONDS", "30")),
            "semantic_similarity_threshold": float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.7"))
        },
        "context": {
            "max_context_tokens": int(os.getenv("MAX_CONTEXT_TOKENS", "8000")),
            "system_tokens": int(os.getenv("SYSTEM_TOKENS", "300")),
            "long_term_tokens": int(os.getenv("LONG_TERM_TOKENS", "300")),
            "working_memory_tokens": int(os.getenv("WORKING_MEMORY_TOKENS", "700")),
            "semantic_retrieval_tokens": int(os.getenv("SEMANTIC_RETRIEVAL_TOKENS", "1200"))
        },
        "debug": {
            "enable_debug_logging": os.getenv("ENABLE_DEBUG_LOGGING", "false").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "enable_performance_monitoring": os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
        }
    }


def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get a specific configuration value using dot notation"""
    config = get_system_config()
    
    # Split the key path (e.g., "observability.log_decisions_to_file")
    keys = key_path.split(".")
    
    # Navigate through the config dictionary
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled"""
    return get_config_value("debug.enable_debug_logging", False)


def get_log_level() -> str:
    """Get the configured log level"""
    return get_config_value("debug.log_level", "INFO")