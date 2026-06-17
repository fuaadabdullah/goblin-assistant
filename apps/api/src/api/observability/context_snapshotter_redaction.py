from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Tuple


def extract_context_content(context_layers: List[Dict[str, Any]]) -> str:
    content_parts = []
    for layer in context_layers:
        if "content" in layer:
            content_parts.append(layer["content"])
        elif "text" in layer:
            content_parts.append(layer["text"])
    return "\n".join(content_parts)


def calculate_context_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def redact_text(text: str, custom_patterns: List[str]) -> Tuple[str, List[str]]:
    redacted_text = text
    patterns_found = []

    ssn_pattern = r"\b(\d{3})-(\d{2})-(\d{4})\b"
    if re.search(ssn_pattern, text):
        redacted_text = re.sub(ssn_pattern, r"XXX-XX-XXXX", redacted_text)
        patterns_found.append("ssn")

    cc_pattern = r"\b(\d{4})[\s-](\d{4})[\s-](\d{4})[\s-](\d{4})\b"
    if re.search(cc_pattern, text):
        redacted_text = re.sub(cc_pattern, r"XXXX-XXXX-XXXX-XXXX", redacted_text)
        patterns_found.append("credit_card")

    email_pattern = r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b"
    if re.search(email_pattern, text):
        redacted_text = re.sub(email_pattern, r"[REDACTED_EMAIL]", redacted_text)
        patterns_found.append("email")

    phone_pattern = r"\b(\d{3})-(\d{3})-(\d{4})\b"
    if re.search(phone_pattern, text):
        redacted_text = re.sub(phone_pattern, r"XXX-XXX-XXXX", redacted_text)
        patterns_found.append("phone")

    ip_pattern = r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b"
    if re.search(ip_pattern, text):
        redacted_text = re.sub(ip_pattern, r"XXX.XXX.XXX.XXX", redacted_text)
        patterns_found.append("ip_address")

    for pattern in custom_patterns:
        if re.search(pattern, text):
            redacted_text = re.sub(pattern, "[REDACTED]", redacted_text)
            patterns_found.append("custom_pattern")

    return redacted_text, patterns_found


def redact_context_layers(
    context_layers: List[Dict[str, Any]],
    custom_patterns: List[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    redaction_details = {
        "patterns_applied": [],
        "items_redacted": 0,
        "layers_processed": len(context_layers),
    }
    redacted_layers = []

    for layer in context_layers:
        redacted_layer = layer.copy()
        if "content" in redacted_layer:
            redacted_content, patterns_found = redact_text(
                redacted_layer["content"], custom_patterns
            )
            redacted_layer["content"] = redacted_content
            if patterns_found:
                redaction_details["patterns_applied"].extend(patterns_found)
                redaction_details["items_redacted"] += len(patterns_found)
        redacted_layers.append(redacted_layer)

    return redacted_layers, redaction_details
