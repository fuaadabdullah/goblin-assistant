"""
Pytest configuration and shared fixtures for API tests.
"""

import pytest
import sys
from unittest.mock import MagicMock, AsyncMock


# Mock embedding service before any imports that depend on it
@pytest.fixture(scope="session", autouse=True)
def mock_embedding_service():
    """Mock the embedding service to prevent initialization errors in tests"""
    # Create mock modules
    mock_providers = MagicMock()
    mock_embedding = MagicMock()
    
    # Make async methods work properly
    mock_embedding.EmbeddingService = MagicMock()
    mock_embedding.AsyncEmbeddingWorker = MagicMock()
    
    # Register the mocks before importing
    sys.modules['api.services.providers'] = mock_providers
    sys.modules['api.services.embedding_service'] = mock_embedding
    
    yield
    
    # Cleanup
    sys.modules.pop('api.services.providers', None)
    sys.modules.pop('api.services.embedding_service', None)
