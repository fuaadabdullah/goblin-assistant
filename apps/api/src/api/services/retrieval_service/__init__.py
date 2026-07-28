"""
Retrieval Service — public package interface.

Re‑exports every symbol that callers previously imported from the
single‑file ``retrieval_service.py``.  No call‑site changes needed.
"""

from ._context_bundle import build_context_bundle
from ._limits import (
    PROMPT_RETRIEVAL_MAX,
    PROMPT_RETRIEVAL_MIN,
    clamp_memory_search_limit,
    clamp_prompt_retrieval_k,
    select_top_memory_facts,
)
from ._retrieval_service import ContextBuilder, RetrievalService, retrieval_service
from ._sql_retrieval import (
    FINANCE_BOOST_FACTOR,
    FINANCE_CATEGORIES,
    GENERIC_BOOST_FACTOR,
    SUMMARY_BOOST_FACTOR,
    retrieve_by_source_type,
    retrieve_graph_expanded_memories,
)
from ._token_budget import apply_context_token_budget, estimate_tokens, trim_item_to_token_budget

__all__ = [
    "RetrievalService",
    "ContextBuilder",
    "retrieval_service",
    "FINANCE_CATEGORIES",
    "FINANCE_BOOST_FACTOR",
    "GENERIC_BOOST_FACTOR",
    "SUMMARY_BOOST_FACTOR",
    "estimate_tokens",
    "trim_item_to_token_budget",
    "apply_context_token_budget",
    "build_context_bundle",
    "PROMPT_RETRIEVAL_MIN",
    "PROMPT_RETRIEVAL_MAX",
    "clamp_prompt_retrieval_k",
    "clamp_memory_search_limit",
    "select_top_memory_facts",
    "retrieve_by_source_type",
    "retrieve_graph_expanded_memories",
]
