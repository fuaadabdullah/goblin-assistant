import pytest
from fastapi import HTTPException

from api.parse_router import ParseRequest, parse_orchestration


@pytest.mark.asyncio
async def test_parse_orchestration_success(monkeypatch):
    # Arrange: mock the underlying parser to return a simple plan
    class DummyPlan:
        def __init__(self):
            self.steps = []
            self.estimated_duration = 0
            self.complexity = "low"

    def fake_parse(text, default):
        return DummyPlan()

    monkeypatch.setattr("api.parse_router.parse_natural_language", fake_parse)

    # Act
    req = ParseRequest(text="do something")
    result = await parse_orchestration(req)

    # Assert
    assert hasattr(result, "steps")
    assert result.complexity in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_parse_orchestration_failure(monkeypatch):
    # Arrange: make parser raise
    def bad_parse(text, default):
        raise RuntimeError("boom")

    monkeypatch.setattr("api.parse_router.parse_natural_language", bad_parse)

    # Act / Assert
    req = ParseRequest(text="do something")
    with pytest.raises(HTTPException) as exc:
        await parse_orchestration(req)

    assert exc.value.status_code == 500
