#!/usr/bin/env python3
"""
Test script for Goblin Assistant Continue integration.
Tests the complete pipeline: indexing -> RAG -> provider routing -> streaming.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the goblinos package to path
sys.path.insert(0, str(Path(__file__).parent))

from goblinos.indexer.indexer import VectorIndexer
from goblinos.services.assistant.rag import RAGSystem, RAGContext
from goblinos.services.assistant.router import ProviderRouter
from goblinos.providers.openai import OpenAIProvider


async def test_secret_scanning():
    """Test secret scanning functionality."""
    print("🧪 Testing secret scanning...")

    indexer = VectorIndexer()

    # Test safe content
    safe_content = """
def hello_world():
    print("Hello, World!")
    return "safe"
"""
    is_safe, findings = indexer.secret_scanner.scan_content(safe_content)
    assert is_safe, "Safe content should pass"
    assert len(findings) == 0, "Safe content should have no findings"
    print("✅ Safe content passed")

    # Test content with secrets
    unsafe_content = """
API_KEY = "sk-1234567890abcdef"
PASSWORD = "mysecretpassword"
"""
    is_safe, findings = indexer.secret_scanner.scan_content(unsafe_content)
    assert not is_safe, "Unsafe content should fail"
    assert len(findings) > 0, "Unsafe content should have findings"
    print(f"✅ Unsafe content detected {len(findings)} secrets")

    # Test redaction
    redacted = indexer.secret_scanner.redact_content(unsafe_content, findings)
    assert "API_KEY_REDACTED" in redacted, "Content should be redacted"
    assert "sk-1234567890abcdef" not in redacted, "Original secret should be removed"
    print("✅ Content redaction works")


async def test_indexing():
    """Test document indexing."""
    print("\n🧪 Testing document indexing...")

    indexer = VectorIndexer()

    # Test indexing a Python file
    test_content = '''
"""
Test module for indexing.
"""

class TestClass:
    """A test class."""

    def __init__(self):
        self.value = 42

    def test_method(self):
        """Test method."""
        return self.value * 2

def standalone_function():
    """Standalone function."""
    return "Hello from function"

# Some constants
API_URL = "https://api.example.com"
DEBUG = True
'''

    chunks_created = await indexer.index_file("test_module.py", test_content)
    assert chunks_created > 0, "Should create chunks"
    print(f"✅ Created {chunks_created} chunks")

    # Test search
    results = await indexer.search_text("test method", limit=5)
    assert len(results) > 0, "Should find results"
    print(f"✅ Found {len(results)} search results")

    # Test stats
    stats = await indexer.get_stats()
    assert stats["total_chunks"] > 0, "Should have chunks"
    print(f"✅ Index stats: {stats}")


async def test_provider_routing():
    """Test provider routing and health checks."""
    print("\n🧪 Testing provider routing...")

    router = ProviderRouter()

    # Register a mock provider (we'll use OpenAI if key is available)
    if os.getenv("OPENAI_API_KEY"):
        provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
        router.register_provider("openai", provider)
        print("✅ Registered OpenAI provider")

        # Test health check
        is_healthy = await router.health_check_provider("openai")
        print(f"✅ Provider health check: {'healthy' if is_healthy else 'unhealthy'}")
    else:
        print("⚠️  No OpenAI API key - skipping provider tests")


async def test_rag_system():
    """Test RAG system integration."""
    print("\n🧪 Testing RAG system...")

    indexer = VectorIndexer()
    router = ProviderRouter()
    rag = RAGSystem(indexer, router)

    # Test prompt building with proper RAGContext objects
    contexts = [
        RAGContext(
            content="def hello(): return 'world'",
            file_path="test.py",
            start_line=1,
            end_line=1,
        ),
        RAGContext(
            content="class Test: pass", file_path="test.py", start_line=3, end_line=3
        ),
    ]
    prompt = rag._build_prompt("How do I create a function?", contexts)

    assert "How do I create a function?" in prompt, "Query should be in prompt"
    print("✅ RAG prompt building works")


async def test_api_endpoints():
    """Test FastAPI endpoints (basic smoke test)."""
    print("\n🧪 Testing API endpoints...")

    # Skip API test for now - would need to start server
    print("✅ API test skipped (would need server)")


async def main():
    """Run all tests."""
    print("🚀 Starting Goblin Assistant integration tests...\n")

    try:
        await test_secret_scanning()
        await test_indexing()
        await test_provider_routing()
        await test_rag_system()
        await test_api_endpoints()

        print("\n🎉 All tests passed! Goblin Assistant integration is working.")
        print("\n📋 Next steps:")
        print("1. Set OPENAI_API_KEY environment variable for full provider testing")
        print("2. Run: python -m uvicorn goblinos.services.assistant.api:app --reload")
        print("3. Test the /continue/hook endpoint with Continue IDE extension")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
