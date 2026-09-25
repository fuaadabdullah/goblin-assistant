from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from api.providers.supabase_events import _fire


def test_fire_does_not_create_coroutine_without_running_loop():
    coroutine_factory = Mock()

    _fire(coroutine_factory)

    coroutine_factory.assert_not_called()


@pytest.mark.asyncio
async def test_fire_schedules_factory_coroutine_on_running_loop():
    operation = AsyncMock()

    _fire(operation)

    await asyncio.sleep(0)
    operation.assert_awaited_once_with()
