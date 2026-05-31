"""Tests for the shared embedding service."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_real_embedding_module():
    module_path = Path(__file__).resolve().parents[1] / "services" / (
        "embedding_service.py"
    )
    spec = importlib.util.spec_from_file_location(
        "api.services.embedding_service_real",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_defaults_to_openai_provider(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    module = _load_real_embedding_module()
    service = module.EmbeddingService()

    assert service.provider_name == "openai"
    assert service.model == "text-embedding-3-small"


def test_uses_env_selected_mock_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")

    module = _load_real_embedding_module()
    service = module.EmbeddingService()

    assert service.provider_name == "mock"
    assert service.client.__class__.__name__ == "MockProvider"


@pytest.mark.asyncio
async def test_embed_text_uses_mock_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")

    module = _load_real_embedding_module()
    service = module.EmbeddingService()
    embedding = await service.embed_text("Your text here")

    assert isinstance(embedding, list)
    assert len(embedding) == 32
    assert all(isinstance(value, float) for value in embedding)


@pytest.mark.asyncio
async def test_embed_batch_uses_mock_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")

    module = _load_real_embedding_module()
    service = module.EmbeddingService()
    embeddings = await service.embed_batch(["alpha", "beta"])

    assert len(embeddings) == 2
    assert all(len(vector) == 32 for vector in embeddings)


@pytest.mark.asyncio
async def test_empty_input_returns_empty_embedding(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")

    module = _load_real_embedding_module()
    service = module.EmbeddingService()

    assert await service.embed_text("") == []
    assert await service.embed_batch([]) == []
