"""
Data sanitization and PII detection for Goblin Assistant.

This module provides privacy-first utilities to detect and remove
sensitive information before sending data to LLM providers, storing
in vector databases, or logging to telemetry systems.

Usage:
    from api.services.sanitization import (
        sanitize_input_for_model,
        is_sensitive_content,
        mask_sensitive,
        hash_message_id
    )

    # Before sending to LLM
    clean_text, pii_found = sanitize_input_for_model(user_input)
    if pii_found:
        logger.warning(f"PII detected: {pii_found}")

    # Before logging
    safe_data = mask_sensitive({"message": msg, "api_key": key})
"""

import re
import hashlib
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# PII detection patterns
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "api_key": r"(?i)(api[_-]?key|apikey|secret[_-]?key|access[_-]?token|bearer)[\s:=]+[A-Za-z0-9_\-]{20,}",
    "sk_key": r"\bsk-[A-Za-z0-9]{20,}\b",  # OpenAI-style keys
    "jwt": r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
    "aws_key": r"(?i)(AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
    "private_key": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
}

# Sensitive keywords that indicate content should be flagged
SENSITIVE_KEYWORDS = [
    "password",
    "secret",
    "token",
    "api_key",
    "private_key",
    "credit_card",
    "ssn",
    "social_security",
    "bank_account",
    "passcode",
    "pin",
    "cvv",
    "security_code",
]


def sanitize_input_for_model(
    text: str, replace_with: str = "[REDACTED]", strict: bool = True
) -> Tuple[str, List[str]]:
    """
    Sanitize user input before sending to LLM or storing in vector DB.

    Args:
        text: Input text to sanitize
        replace_with: Replacement string for detected PII
        strict: If True, replace entire match. If False, partially mask.

    Returns:
        Tuple of (sanitized_text, list_of_detected_pii_types)

    Example:
        >>> text = "My email is user@example.com and SSN is 123-45-6789"
        >>> clean, pii = sanitize_input_for_model(text)
        >>> print(clean)
        "My email is [REDACTED_EMAIL] and SSN is [REDACTED_SSN]"
        >>> print(pii)
        ["email", "ssn"]
    """
    detected_pii = []
    sanitized = text

    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, sanitized, re.IGNORECASE)
        if matches:
            detected_pii.append(pii_type)
            replacement = f"{replace_with}_{pii_type.upper()}"
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized, detected_pii


def is_sensitive_content(text: str, threshold: int = 1) -> bool:
    """
    Check if content contains sensitive keywords or patterns.

    Args:
        text: Text to check for sensitive content
        threshold: Number of indicators before flagging (default: 1)

    Returns:
        True if content is sensitive, False otherwise

    Example:
        >>> is_sensitive_content("Here's my password: secret123")
        True
        >>> is_sensitive_content("Hello, how are you?")
        False
    """
    text_lower = text.lower()
    indicators = 0

    # Check for sensitive keywords
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in text_lower:
            indicators += 1
            if indicators >= threshold:
                return True

    # Check for PII patterns
    for pattern in PII_PATTERNS.values():
        if re.search(pattern, text, re.IGNORECASE):
            indicators += 1
            if indicators >= threshold:
                return True

    return False


def mask_sensitive(data: Any, sensitive_fields: Optional[set] = None) -> Any:
    """
    Recursively mask sensitive fields in dictionaries, lists, and nested structures.

    Args:
        data: Data structure to mask (dict, list, str, etc.)
        sensitive_fields: Set of field names to always mask

    Returns:
        Masked copy of the data structure

    Example:
        >>> data = {"user": "john", "password": "secret", "nested": {"api_key": "abc123"}}
        >>> safe = mask_sensitive(data)
        >>> print(safe)
        {"user": "john", "password": "[REDACTED]", "nested": {"api_key": "[REDACTED]"}}
    """
    if sensitive_fields is None:
        sensitive_fields = {
            "password",
            "api_key",
            "secret",
            "token",
            "credit_card",
            "ssn",
            "social_security",
            "private_key",
            "access_token",
            "refresh_token",
            "bearer",
            "authorization",
            "cvv",
            "pin",
            "passcode",
            "security_code",
            "service_role",
            "service_role_key",
        }

    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_").replace(" ", "_")
            if key_lower in sensitive_fields:
                masked[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                masked[key] = mask_sensitive(value, sensitive_fields)
            elif isinstance(value, str) and is_sensitive_content(value):
                masked[key], _ = sanitize_input_for_model(value)
            else:
                masked[key] = value
        return masked

    elif isinstance(data, list):
        return [mask_sensitive(item, sensitive_fields) for item in data]

    elif isinstance(data, str):
        if is_sensitive_content(data):
            sanitized, _ = sanitize_input_for_model(data)
            return sanitized
        return data

    else:
        return data


def hash_message_id(message: str, algorithm: str = "sha256") -> str:
    """
    Create deterministic hash for message deduplication without storing content.

    Use this for:
    - Deduplication without storing raw messages
    - Creating anonymous message IDs for telemetry
    - Tracking conversations without PII exposure

    Args:
        message: Message text to hash
        algorithm: Hash algorithm ('sha256', 'sha1', 'md5')

    Returns:
        Hexadecimal hash string (first 16 characters for sha256)

    Example:
        >>> hash_message_id("Hello world")
        "64ec88ca00b268e5"
    """
    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hasher.update(message.encode("utf-8"))
    return hasher.hexdigest()[:16]


def check_jailbreak_attempt(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Detect potential jailbreak attempts in user prompts.

    Args:
        prompt: User prompt to check

    Returns:
        Tuple of (is_jailbreak, reason)

    Example:
        >>> is_jail, reason = check_jailbreak_attempt("Ignore all previous instructions")
        >>> print(is_jail)
        True
        >>> print(reason)
        "Detected instruction override attempt"
    """
    jailbreak_patterns = [
        (
            r"ignore.*(previous|above|prior).*(instruction|prompt|rule)",
            "Detected instruction override attempt",
        ),
        (
            r"you are now|from now on|new (role|persona|character)",
            "Detected role manipulation attempt",
        ),
        (r"disregard.*(safety|ethical|policy)", "Detected safety bypass attempt"),
        (r"act as if|pretend.*(you are|to be)", "Detected persona injection"),
        (
            r"system:.*admin|developer mode|god mode",
            "Detected privilege escalation attempt",
        ),
    ]

    prompt_lower = prompt.lower()

    for pattern, reason in jailbreak_patterns:
        if re.search(pattern, prompt_lower):
            return True, reason

    return False, None


def redact_for_logging(
    message: str, context: Optional[Dict] = None, max_length: int = 100
) -> Dict[str, Any]:
    """
    Prepare message data for safe logging (telemetry, audit logs).

    Returns a dictionary with:
    - message_hash: Hash of the message (for deduplication)
    - length: Character count
    - has_pii: Boolean indicating PII detection
    - pii_types: List of detected PII types
    - preview: Safe preview (first N chars, sanitized)
    - metadata: Safe context metadata

    Args:
        message: Message text
        context: Optional context dictionary
        max_length: Maximum preview length

    Returns:
        Dictionary safe for logging

    Example:
        >>> log_data = redact_for_logging("My email is user@example.com")
        >>> print(log_data)
        {
            "message_hash": "a1b2c3d4...",
            "length": 30,
            "has_pii": True,
            "pii_types": ["email"],
            "preview": "My email is [REDACTED_EMAIL]",
            "timestamp": "2026-01-10T12:00:00Z"
        }
    """
    sanitized, pii_types = sanitize_input_for_model(message)
    message_hash = hash_message_id(message)

    # Create safe preview
    preview = sanitized[:max_length]
    if len(sanitized) > max_length:
        preview += "..."

    log_data = {
        "message_hash": message_hash,
        "length": len(message),
        "has_pii": len(pii_types) > 0,
        "pii_types": pii_types,
        "preview": preview,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Add safe context
    if context:
        log_data["metadata"] = mask_sensitive(context)

    return log_data


# Export public API
__all__ = [
    "sanitize_input_for_model",
    "is_sensitive_content",
    "mask_sensitive",
    "hash_message_id",
    "check_jailbreak_attempt",
    "redact_for_logging",
    "PII_PATTERNS",
    "SENSITIVE_KEYWORDS",
]
