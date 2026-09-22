from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from api.providers.base import ProviderErrorCategory
from api.services import background_tasks


@pytest.mark.asyncio
async def test_summary_retry_stops_on_auth_failure(monkeypatch) -> None:
    invoke = AsyncMock(
        return_value={
            "ok": False,
            "error": "invalid key",
            "error_category": ProviderErrorCategory.AUTH.value,
        }
    )
    monkeypatch.setattr(background_tasks, "invoke_provider", invoke)

    result = await background_tasks.BackgroundTaskManager()._generate_summary_with_retry(
        "summarize this",
        max_retries=3,
    )

    assert result is None
    assert invoke.await_count == 1


@pytest.mark.asyncio
async def test_summary_retry_retries_transient_server_failure(monkeypatch) -> None:
    invoke = AsyncMock(
        side_effect=[
            {
                "ok": False,
                "error": "provider unavailable",
                "error_category": ProviderErrorCategory.SERVER_ERROR.value,
            },
            {
                "ok": True,
                "result": {"text": "summary"},
            },
        ]
    )
    monkeypatch.setattr(background_tasks, "invoke_provider", invoke)

    result = await background_tasks.BackgroundTaskManager()._generate_summary_with_retry(
        "summarize this",
        max_retries=3,
    )

    assert result == "summary"
    assert invoke.await_count == 2
