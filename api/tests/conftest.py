"""
Pytest configuration and shared fixtures for API tests.
"""

import pytest
import sys
import types
from unittest.mock import MagicMock, AsyncMock
from fastapi import APIRouter


def _router_module(name: str, prefix: str, tag: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.router = APIRouter(prefix=prefix, tags=[tag])
    return module


class _ArtifactCleanupServiceStub:
    async def start(self):
        return None

    async def stop(self):
        return None


if "api.sandbox_api" not in sys.modules:
    sys.modules["api.sandbox_api"] = _router_module(
        "api.sandbox_api",
        "/sandbox",
        "sandbox",
    )

if "api.routes.privacy" not in sys.modules:
    sys.modules["api.routes.privacy"] = _router_module(
        "api.routes.privacy",
        "/api/privacy",
        "privacy",
    )

if "api.artifact_cleanup" not in sys.modules:
    artifact_cleanup_module = types.ModuleType("api.artifact_cleanup")
    artifact_cleanup_module.artifact_cleanup_service = _ArtifactCleanupServiceStub()
    sys.modules["api.artifact_cleanup"] = artifact_cleanup_module


from api.conftest import _build_authenticated_client


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


# Mock embedding service before any imports that depend on it
@pytest.fixture(scope="session", autouse=True)
def mock_embedding_service():
    """Mock the embedding service to prevent initialization errors in tests"""
    # Create mock modules
    mock_providers = MagicMock()
    mock_embedding = types.ModuleType("api.services.embedding_service")
    mock_embedding.EmbeddingProviderUnavailableError = RuntimeError
    mock_embedding.EmbeddingService = _EmbeddingServiceStub
    mock_embedding.AsyncEmbeddingWorker = _AsyncEmbeddingWorkerStub
    mock_embedding.embedding_worker = _AsyncEmbeddingWorkerStub()
    
    # Register the mocks before importing
    sys.modules['api.services.providers'] = mock_providers
    sys.modules['api.services.embedding_service'] = mock_embedding
    
    yield
    
    # Cleanup
    sys.modules.pop('api.services.providers', None)
    sys.modules.pop('api.services.embedding_service', None)


__all__ = ["_build_authenticated_client"]
