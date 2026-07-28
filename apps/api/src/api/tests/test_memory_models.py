"""Tests for storage/memory_models.py — SQLAlchemy model definitions."""

from __future__ import annotations

# ── Import coverage — model classes are defined at import time ────────────────


class TestMemoryModelsImport:
    def test_memory_item_model_importable(self):
        from api.storage.memory_models import MemoryItemModel

        assert MemoryItemModel.__tablename__ == "memory_items"

    def test_memory_promotion_log_model_importable(self):
        from api.storage.memory_models import MemoryPromotionLogModel

        assert MemoryPromotionLogModel.__tablename__ == "memory_promotion_log"

    def test_memory_fact_extraction_model_importable(self):
        from api.storage.memory_models import MemoryFactExtractionModel

        assert MemoryFactExtractionModel.__tablename__ == "memory_fact_extraction"

    def test_memory_consistency_model_importable(self):
        from api.storage.memory_models import MemoryConsistencyModel

        assert MemoryConsistencyModel.__tablename__ == "memory_consistency"

    def test_memory_usage_model_importable(self):
        from api.storage.memory_models import MemoryUsageModel

        assert MemoryUsageModel.__tablename__ == "memory_usage"

    def test_base_importable(self):
        from api.storage.memory_models import Base

        assert Base is not None


# ── MemoryItemModel columns ───────────────────────────────────────────────────


class TestMemoryItemModelColumns:
    def test_has_id_column(self):
        from api.storage.memory_models import MemoryItemModel

        cols = {c.name for c in MemoryItemModel.__table__.columns}
        assert "id" in cols

    def test_has_user_id_column(self):
        from api.storage.memory_models import MemoryItemModel

        cols = {c.name for c in MemoryItemModel.__table__.columns}
        assert "user_id" in cols

    def test_has_fact_text_column(self):
        from api.storage.memory_models import MemoryItemModel

        cols = {c.name for c in MemoryItemModel.__table__.columns}
        assert "fact_text" in cols

    def test_has_confidence_column(self):
        from api.storage.memory_models import MemoryItemModel

        cols = {c.name for c in MemoryItemModel.__table__.columns}
        assert "confidence" in cols

    def test_has_promotion_status_column(self):
        from api.storage.memory_models import MemoryItemModel

        cols = {c.name for c in MemoryItemModel.__table__.columns}
        assert "promotion_status" in cols

    def test_has_created_at_column(self):
        from api.storage.memory_models import MemoryItemModel

        cols = {c.name for c in MemoryItemModel.__table__.columns}
        assert "created_at" in cols

    def test_has_indexes(self):
        from api.storage.memory_models import MemoryItemModel

        assert len(MemoryItemModel.__table__.indexes) > 0


# ── MemoryPromotionLogModel columns ──────────────────────────────────────────


class TestMemoryPromotionLogModelColumns:
    def test_has_candidate_fact_column(self):
        from api.storage.memory_models import MemoryPromotionLogModel

        cols = {c.name for c in MemoryPromotionLogModel.__table__.columns}
        assert "candidate_fact" in cols

    def test_has_promotion_status_column(self):
        from api.storage.memory_models import MemoryPromotionLogModel

        cols = {c.name for c in MemoryPromotionLogModel.__table__.columns}
        assert "promotion_status" in cols


# ── MemoryFactExtractionModel columns ────────────────────────────────────────


class TestMemoryFactExtractionModelColumns:
    def test_has_message_id_column(self):
        from api.storage.memory_models import MemoryFactExtractionModel

        cols = {c.name for c in MemoryFactExtractionModel.__table__.columns}
        assert "message_id" in cols

    def test_has_extracted_facts_column(self):
        from api.storage.memory_models import MemoryFactExtractionModel

        cols = {c.name for c in MemoryFactExtractionModel.__table__.columns}
        assert "extracted_facts" in cols


# ── MemoryConsistencyModel columns ────────────────────────────────────────────


class TestMemoryConsistencyModelColumns:
    def test_has_similarity_score_column(self):
        from api.storage.memory_models import MemoryConsistencyModel

        cols = {c.name for c in MemoryConsistencyModel.__table__.columns}
        assert "similarity_score" in cols

    def test_has_consistency_score_column(self):
        from api.storage.memory_models import MemoryConsistencyModel

        cols = {c.name for c in MemoryConsistencyModel.__table__.columns}
        assert "consistency_score" in cols


# ── MemoryUsageModel columns ──────────────────────────────────────────────────


class TestMemoryUsageModelColumns:
    def test_has_query_text_column(self):
        from api.storage.memory_models import MemoryUsageModel

        cols = {c.name for c in MemoryUsageModel.__table__.columns}
        assert "query_text" in cols

    def test_has_total_retrieval_score_column(self):
        from api.storage.memory_models import MemoryUsageModel

        cols = {c.name for c in MemoryUsageModel.__table__.columns}
        assert "total_retrieval_score" in cols


# ── add_memory_relationships helper ──────────────────────────────────────────


class TestAddMemoryRelationships:
    def test_add_memory_relationships_is_callable(self):
        from api.storage.memory_models import add_memory_relationships

        assert callable(add_memory_relationships)
