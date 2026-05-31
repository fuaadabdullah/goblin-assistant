"""
Retrieval Service — public package interface.

Re‑exports every symbol that callers previously imported from the
single‑file ``retrieval_service.py``.  No call‑site changes needed.
"""

from ._retrieval_service import RetrievalService, ContextBuilder, retrieval_service
from ._sql_retrieval import (
    FINANCE_CATEGORIES,
    FINANCE_BOOST_FACTOR,
    GENERIC_BOOST_FACTOR,
    SUMMARY_BOOST_FACTOR,
)
from ._token_budget import estimate_tokens, trim_item_to_token_budget, apply_context_token_budget
from ._context_bundle import build_context_bundle

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
]