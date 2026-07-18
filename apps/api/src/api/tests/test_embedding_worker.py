from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.services.embedding_worker import AsyncEmbeddingWorker


@pytest.mark.asyncio
async def test_worker_processes_message_with_configured_service_factory():
    service = SimpleNamespace(store_message_embedding=AsyncMock())
    worker = AsyncEmbeddingWorker(service_factory=lambda: service)

    await worker._process_task(
        {
            "type": "message",
            "user_id": "u1",
            "conversation_id": "c1",
            "message_id": "m1",
            "content": "hello",
            "metadata": {"source": "test"},
        }
    )

    service.store_message_embedding.assert_awaited_once_with(
        user_id="u1",
        conversation_id="c1",
        message_id="m1",
        content="hello",
        metadata={"source": "test"},
    )


@pytest.mark.asyncio
async def test_worker_requires_service_factory_when_processing_jobs():
    worker = AsyncEmbeddingWorker()

    with pytest.raises(RuntimeError, match="service factory"):
        await worker._process_task(
            {
                "type": "summary",
                "conversation_id": "c1",
                "summary_text": "summary",
            }
        )
