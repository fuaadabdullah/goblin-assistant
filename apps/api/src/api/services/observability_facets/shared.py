from __future__ import annotations

import hashlib

from ..observability_models import RetrievalTier


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def redact_content(content: str) -> str:
    if len(content) > 100:
        return content[:100] + "...[REDACTED]..."
    return content


def map_layer_to_tier(layer_name: str) -> RetrievalTier:
    tier_mapping = {
        "system": RetrievalTier.LONG_TERM,
        "long_term_memory": RetrievalTier.LONG_TERM,
        "working_memory": RetrievalTier.WORKING_MEMORY,
        "semantic_retrieval": RetrievalTier.SEMANTIC,
        "ephemeral_memory": RetrievalTier.EPHEMERAL,
    }
    return tier_mapping.get(layer_name, RetrievalTier.SEMANTIC)
