"""
Tests for finance-domain memory pipeline and HybridRouter instrumentation.
Covers:
  - Finance message classification (entities, risk, regulatory, portfolio, macro)
  - Finance-specific promotion gates
  - Finance memory category classification
  - Finance retrieval boost constants
  - HybridRouter score breakdown + audit trail
  - Routing cost-weight tuning boundary conditions
"""

import re
import sys
import types
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

# ── Pre-patch embedding service so memory-chain imports succeed ──────
# The embedding_service module tries to resolve a provider at import time.
# We inject a lightweight stub into sys.modules before importing anything
# from the memory/retrieval pipeline.

if "api.services.embedding_service" not in sys.modules:
    _stub_mod = types.ModuleType("api.services.embedding_service")

    class _EmbeddingServiceStub:
        async def embed_text(self, _text: str):
            return []

    class _AsyncEmbeddingWorkerStub:
        def __init__(self):
            self.start = AsyncMock()
            self.stop = AsyncMock()
            self.queue_message_embedding = AsyncMock()
            self.queue_summary_embedding = AsyncMock()
            self.queue_memory_embedding = AsyncMock()

    _stub_mod.EmbeddingService = _EmbeddingServiceStub
    _stub_mod.AsyncEmbeddingWorker = _AsyncEmbeddingWorkerStub
    _stub_mod.EmbeddingProviderUnavailableError = RuntimeError
    _stub_mod.embedding_worker = _AsyncEmbeddingWorkerStub()
    sys.modules["api.services.embedding_service"] = _stub_mod

from api.services.message_classifier import MessageClassifier, MessageType
from api.services.memory_promotion_service import (
    MemoryPromotionService,
    PromotionCandidate,
    PromotionGate,
)
from api.services.retrieval_service import (
    FINANCE_BOOST_FACTOR,
    FINANCE_CATEGORIES,
    GENERIC_BOOST_FACTOR,
)
from api.routing.router import HybridRouter, RoutingRegistry


# ── Message Classifier: finance types ────────────────────────────────

class TestFinanceClassification:
    def setup_method(self):
        self.classifier = MessageClassifier()

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("AAPL stock price is up 5% after earnings", MessageType.FINANCIAL_ENTITY),
            ("Our position in the S&P 500 ETF is overweight", MessageType.FINANCIAL_ENTITY),
            ("Treasury bond yields rose this week", MessageType.FINANCIAL_ENTITY),
        ],
    )
    def test_financial_entity_classification(self, content, expected):
        result = self.classifier.classify_message(content, "user")
        assert result.message_type == expected
        assert result.confidence > 0.0

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("Portfolio volatility increased to 18% annualized", MessageType.RISK_SIGNAL),
            ("The Sharpe ratio dropped below 1.0", MessageType.RISK_SIGNAL),
            ("Max drawdown on the backtest was 12%", MessageType.RISK_SIGNAL),
        ],
    )
    def test_risk_signal_classification(self, content, expected):
        result = self.classifier.classify_message(content, "user")
        assert result.message_type == expected

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("SEC filing deadline is next week for 10-K", MessageType.REGULATORY_REF),
            ("FINRA suitability requirements are strict for advisory accounts", MessageType.REGULATORY_REF),
            ("Dodd-Frank reporting requirements apply here", MessageType.REGULATORY_REF),
        ],
    )
    def test_regulatory_ref_classification(self, content, expected):
        result = self.classifier.classify_message(content, "user")
        assert result.message_type == expected

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("Rebalance the portfolio to target allocation weights", MessageType.PORTFOLIO_ACTION),
            ("Set a stop-loss order on the position at -5%", MessageType.PORTFOLIO_ACTION),
            ("Tax-loss harvest the underperforming lots", MessageType.PORTFOLIO_ACTION),
        ],
    )
    def test_portfolio_action_classification(self, content, expected):
        result = self.classifier.classify_message(content, "user")
        assert result.message_type == expected

    @pytest.mark.parametrize(
        "content,expected",
        [
            ("FOMC rate decision is tomorrow afternoon", MessageType.MACRO_EVENT),
            ("CPI inflation data came in hot this morning", MessageType.MACRO_EVENT),
            ("Non-farm payroll report beat expectations", MessageType.MACRO_EVENT),
        ],
    )
    def test_macro_event_classification(self, content, expected):
        result = self.classifier.classify_message(content, "user")
        assert result.message_type == expected

    def test_generic_chat_not_classified_as_finance(self):
        result = self.classifier.classify_message("Hey, how's your day going?", "user")
        assert result.message_type not in {
            MessageType.FINANCIAL_ENTITY, MessageType.RISK_SIGNAL,
            MessageType.REGULATORY_REF, MessageType.PORTFOLIO_ACTION,
            MessageType.MACRO_EVENT,
        }


# ── Promotion: finance category classification ───────────────────────

class TestFinanceCategoryClassification:
    def setup_method(self):
        self.service = MemoryPromotionService()

    @pytest.mark.parametrize(
        "content,expected_category",
        [
            ("The fund holds mostly treasury bonds and equities", "instrument"),
            ("Portfolio volatility reached 20% during backtest", "risk_signal"),
            ("FINRA suitability rules require documentation", "regulatory_constraint"),
            ("Rebalance to target allocation next quarter", "portfolio_action"),
            ("FOMC rate hike expected in March", "macro_event"),
        ],
    )
    def test_finance_category_detection(self, content, expected_category):
        category = self.service._classify_memory_category(content)
        assert category == expected_category

    def test_emotional_content_rejected(self):
        category = self.service._classify_memory_category(
            "I feel stressed about the market today"
        )
        assert category is None


# ── Promotion: finance-specific gates ────────────────────────────────

class TestFinancePromotionGates:
    def setup_method(self):
        self.service = MemoryPromotionService()

    def test_entity_plausibility_passes_for_real_instrument(self):
        candidate = PromotionCandidate(
            content="AAPL stock has consistently paid dividends",
            category="instrument",
            source_conversation="conv-1",
            source_type="summary",
            confidence=0.9,
            metadata={},
            created_at=datetime.utcnow(),
        )
        result = self.service._evaluate_finance_gates(candidate)
        assert PromotionGate.ENTITY_PLAUSIBILITY in result["passed"]

    def test_entity_plausibility_fails_for_gibberish(self):
        candidate = PromotionCandidate(
            content="XYZQT is something random",
            category="instrument",
            source_conversation="conv-1",
            source_type="summary",
            confidence=0.5,
            metadata={},
            created_at=datetime.utcnow(),
        )
        result = self.service._evaluate_finance_gates(candidate)
        assert PromotionGate.ENTITY_PLAUSIBILITY in result["failed"]

    def test_risk_context_passes_with_numeric_anchor(self):
        candidate = PromotionCandidate(
            content="Portfolio volatility increased to 18% VaR",
            category="risk_signal",
            source_conversation="conv-1",
            source_type="summary",
            confidence=0.85,
            metadata={},
            created_at=datetime.utcnow(),
        )
        result = self.service._evaluate_finance_gates(candidate)
        assert PromotionGate.RISK_CONTEXT in result["passed"]

    def test_risk_context_fails_without_anchor(self):
        candidate = PromotionCandidate(
            content="There is some volatility risk",
            category="risk_signal",
            source_conversation="conv-1",
            source_type="summary",
            confidence=0.6,
            metadata={},
            created_at=datetime.utcnow(),
        )
        result = self.service._evaluate_finance_gates(candidate)
        assert PromotionGate.RISK_CONTEXT in result["failed"]

    def test_compliance_marker_flags_sensitive_content(self):
        candidate = PromotionCandidate(
            content="This involves material non-public information from insider trading",
            category="regulatory_constraint",
            source_conversation="conv-1",
            source_type="summary",
            confidence=0.8,
            metadata={},
            created_at=datetime.utcnow(),
        )
        result = self.service._evaluate_finance_gates(candidate)
        assert PromotionGate.COMPLIANCE_MARKER in result["failed"]

    def test_compliance_marker_passes_for_clean_content(self):
        candidate = PromotionCandidate(
            content="SEC fiduciary duty applies to this account type",
            category="regulatory_constraint",
            source_conversation="conv-1",
            source_type="summary",
            confidence=0.9,
            metadata={},
            created_at=datetime.utcnow(),
        )
        result = self.service._evaluate_finance_gates(candidate)
        assert PromotionGate.COMPLIANCE_MARKER in result["passed"]


# ── Retrieval: finance category boost constants ──────────────────────

class TestFinanceRetrievalBoost:
    def test_finance_categories_defined(self):
        assert "instrument" in FINANCE_CATEGORIES
        assert "risk_signal" in FINANCE_CATEGORIES
        assert "regulatory_constraint" in FINANCE_CATEGORIES
        assert "portfolio_action" in FINANCE_CATEGORIES
        assert "macro_event" in FINANCE_CATEGORIES

    def test_finance_boost_exceeds_generic(self):
        assert FINANCE_BOOST_FACTOR > GENERIC_BOOST_FACTOR

    def test_boost_factors_are_positive(self):
        assert FINANCE_BOOST_FACTOR > 0
        assert GENERIC_BOOST_FACTOR > 0


# ── HybridRouter: score breakdown + audit trail ─────────────────────

class TestHybridRouterInstrumentation:
    def test_rank_returns_ordered_candidates(self):
        reg = RoutingRegistry()
        router = HybridRouter(cost_weight=0.35)
        # Inject registry stats
        reg.get("fast_expensive").update_latency(50.0)
        reg.get("fast_expensive").success_count = 10
        reg.get("slow_cheap").update_latency(500.0)
        reg.get("slow_cheap").success_count = 10

        # Override the global registry temporarily via monkeypatch-style:
        import api.routing.router as mod
        original = mod.registry
        mod.registry = reg
        try:
            costs = {
                "fast_expensive": (0.05, 0.10),
                "slow_cheap": (0.001, 0.001),
            }
            ranked = router.rank(["fast_expensive", "slow_cheap"], costs)
            assert isinstance(ranked, list)
            assert len(ranked) == 2
        finally:
            mod.registry = original

    def test_rank_logs_decision_to_audit_trail(self):
        reg = RoutingRegistry()
        router = HybridRouter(cost_weight=0.50)

        import api.routing.router as mod
        original = mod.registry
        mod.registry = reg
        try:
            costs = {"a": (0.01, 0.02), "b": (0.05, 0.10)}
            router.rank(["a", "b"], costs, request_id="test-req-1")
            trail = reg.get_audit_trail(limit=10)
            decisions = [r for r in trail if r["event"] == "decision"]
            assert len(decisions) == 1
            assert decisions[0]["request_id"] == "test-req-1"
            assert decisions[0]["cost_weight"] == 0.50
            assert "a" in decisions[0]["score_breakdown"]
            assert "b" in decisions[0]["score_breakdown"]
            # Score breakdown has expected keys
            for pid in ["a", "b"]:
                bd = decisions[0]["score_breakdown"][pid]
                assert "normalized_latency" in bd
                assert "normalized_cost" in bd
                assert "reliability" in bd
                assert "final_score" in bd
        finally:
            mod.registry = original

    def test_record_success_with_request_id_logs_outcome(self):
        reg = RoutingRegistry()
        reg.record_success(
            "openai",
            latency_ms=150.0,
            cost_usd=0.005,
            request_id="req-42",
            input_tokens=100,
            output_tokens=50,
        )
        trail = reg.get_audit_trail()
        outcomes = [r for r in trail if r["event"] == "outcome"]
        assert len(outcomes) == 1
        assert outcomes[0]["request_id"] == "req-42"
        assert outcomes[0]["actual_latency_ms"] == 150.0
        assert outcomes[0]["input_tokens"] == 100

    def test_record_success_without_request_id_skips_audit(self):
        reg = RoutingRegistry()
        reg.record_success("openai", latency_ms=100.0, cost_usd=0.001)
        trail = reg.get_audit_trail()
        assert len(trail) == 0

    def test_audit_trail_respects_max_capacity(self):
        reg = RoutingRegistry()
        for i in range(1100):
            reg.record_success(
                "p",
                latency_ms=1.0,
                cost_usd=0.0,
                request_id=f"r-{i}",
            )
        trail = reg.get_audit_trail(limit=2000)
        assert len(trail) <= RoutingRegistry._AUDIT_MAX


# ── HybridRouter: cost-weight tuning boundaries ─────────────────────

class TestCostWeightTuning:
    def test_cost_weight_clamped_to_zero(self):
        router = HybridRouter(cost_weight=-0.5)
        assert router.cost_weight == 0.0

    def test_cost_weight_clamped_to_one(self):
        router = HybridRouter(cost_weight=1.5)
        assert router.cost_weight == 1.0

    def test_cost_weight_preserved_in_valid_range(self):
        router = HybridRouter(cost_weight=0.50)
        assert router.cost_weight == 0.50

    def test_increased_cost_weight_changes_ranking(self):
        """Prove that shifting from 0.35→0.65 cost weight can reverse provider order."""
        reg = RoutingRegistry()
        # Provider A: fast but expensive — set latency directly to avoid EWMA lag
        stats_a = reg.get("A")
        stats_a.ewma_latency_ms = 50.0
        stats_a.success_count = 10
        # Provider B: slow but cheap
        stats_b = reg.get("B")
        stats_b.ewma_latency_ms = 5000.0
        stats_b.success_count = 10

        import api.routing.router as mod
        original = mod.registry
        mod.registry = reg
        try:
            costs = {"A": (0.10, 0.20), "B": (0.001, 0.001)}
            rank_35 = HybridRouter(cost_weight=0.35).rank(["A", "B"], costs)
            rank_65 = HybridRouter(cost_weight=0.65).rank(["A", "B"], costs)
            # With extreme cost/latency disparity, rankings should differ
            assert rank_35 != rank_65
        finally:
            mod.registry = original

    def test_empty_candidates_returns_empty(self):
        router = HybridRouter(cost_weight=0.50)
        assert router.rank([], {}) == []
