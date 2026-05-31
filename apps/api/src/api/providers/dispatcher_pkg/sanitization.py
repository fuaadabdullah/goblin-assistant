from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List

_JSON_SECRET_RE = re.compile(
    r'("(?:api[_-]?key|access[_-]?token|authorization|secret|password)"\s*:\s*")([^"]+)(")',
    re.IGNORECASE,
)
_KV_SECRET_RE = re.compile(
    r"((?:api[_-]?key|access[_-]?token|authorization|secret|password)\s*[:=]\s*)([^,\s;]+)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(bearer\s+)([A-Za-z0-9._\-]+)", re.IGNORECASE)
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")

EXTRA_SECRET_ENV_NAMES = {
    "AZURE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "VERTEX_AI_SERVICE_ACCOUNT_JSON",
    "GCP_SERVICE_ACCOUNT_KEY",
}


def known_secrets(configs: Dict[str, Dict[str, Any]]) -> List[str]:
    secrets: set[str] = set()
    for raw_config in configs.values():
        if not isinstance(raw_config, dict):
            continue
        api_key_env = str(raw_config.get("api_key_env", "") or "").strip()
        if not api_key_env:
            continue
        secret = os.getenv(api_key_env, "").strip()
        if secret:
            secrets.add(secret)

    for env_name in EXTRA_SECRET_ENV_NAMES:
        secret = os.getenv(env_name, "").strip()
        if secret:
            secrets.add(secret)
    return list(secrets)


def sanitize_error_message(message: str, secrets: Iterable[str]) -> str:
    sanitized = str(message)
    if not sanitized:
        return sanitized

    for secret in sorted({s for s in secrets if len(s) >= 8}, key=len, reverse=True):
        sanitized = sanitized.replace(secret, "[REDACTED]")

    sanitized = _JSON_SECRET_RE.sub(r"\1[REDACTED]\3", sanitized)
    sanitized = _KV_SECRET_RE.sub(r"\1[REDACTED]", sanitized)
    sanitized = _BEARER_RE.sub(r"\1[REDACTED]", sanitized)
    sanitized = _OPENAI_KEY_RE.sub("[REDACTED]", sanitized)
    return sanitized

