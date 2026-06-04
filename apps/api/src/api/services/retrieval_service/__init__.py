"""
Retrieval Service — public package interface.

Re‑exports every symbol that callers previously imported from the
single‑file ``retrieval_service.py``.  No call‑site changes needed.
"""

from ._context_bundle import build_context_bundle
from ._retrieval_service import ContextBuilder, RetrievalService, retrieval_service
from ._sql_retrieval import (
    FINANCE_BOOST_FACTOR,
    FINANCE_CATEGORIES,
    GENERIC_BOOST_FACTOR,
    SUMMARY_BOOST_FACTOR,
    retrieve_by_source_type,
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
    "retrieve_by_source_type",
]
