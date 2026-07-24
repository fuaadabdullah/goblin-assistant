"""Tests for the profile layer assembly."""

import pytest

from api.services.context_assembly_service import ContextBudget
from api.services.context_assembly_service import profile_layer as prof

# -----------------------------
# format_user_profile tests
# -----------------------------


def test_format_user_profile_empty():
    """Empty profile data returns empty string."""
    assert prof.format_user_profile({}) == ""


def test_format_user_profile_only_header():
    """Profile with no data still shows header."""
    # When no goals, projects, or preferences, should return empty
    assert prof.format_user_profile({"goals": [], "projects": [], "preferences": {}}) == ""


def test_format_user_profile_with_goals():
    """Profile with goals formats correctly."""
    result = prof.format_user_profile({"goals": ["build app", "learn python"]})
    assert "## User Profile" in result
    assert "Goals:" in result
    assert "build app" in result
    assert "learn python" in result


def test_format_user_profile_with_projects():
    """Profile with projects formats correctly."""
    result = prof.format_user_profile({"projects": ["goblin-os", "api-refactor"]})
    assert "Active projects:" in result
    assert "goblin-os" in result


def test_format_user_profile_with_preferences():
    """Profile with preferences formats correctly (limited to 5)."""
    prefs = {f"pref{i}": f"value{i}" for i in range(7)}
    result = prof.format_user_profile({"preferences": prefs})
    assert "Preference - pref0:" in result
    assert "Preference - pref4:" in result
    # Should be limited to first 5
    assert "Preference - pref5:" not in result


def test_format_user_profile_with_key_entities():
    """Profile with key entities formats correctly (limited to 3 types)."""
    entities = {
        "project": [{"value": "project-alpha"}],
        "preference": [{"value": "pref-beta"}],
        "decision": [{"value": "decided-gamma"}],
        "other": [{"value": "should-be-limited"}],
    }
    result = prof.format_user_profile(
        {"key_entities": entities, "preferences": {"k": "v"}}
    )  # needs one non-empty field to show header
    assert "Project:" in result
    assert "Preference:" in result
    assert "Decision:" in result
    assert "Other:" not in result  # limited to 3


# -----------------------------
# assemble_profile_layer tests
# -----------------------------


@pytest.mark.asyncio
async def test_assemble_profile_layer_skips_when_budget_too_small():
    """Profile layer returns None when remaining tokens below threshold."""
    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=50,
        budget=ContextBudget(profile_tokens=200),
    )
    assert layer is None


@pytest.mark.asyncio
async def test_assemble_profile_layer_no_profile_data(monkeypatch):
    """Profile layer returns None when no profile data exists."""
    monkeypatch.setattr(prof, "get_user_profile", lambda _user_id: None)

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )
    assert layer is None


@pytest.mark.asyncio
async def test_assemble_profile_layer_no_relevant_fields(monkeypatch):
    """Profile layer returns None when profile has no goals, projects, or preferences."""

    async def _no_relevant(_user_id):
        return {"key_entities": {}}

    monkeypatch.setattr(prof, "get_user_profile", _no_relevant)

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )
    assert layer is None


@pytest.mark.asyncio
async def test_assemble_profile_layer_success(monkeypatch):
    """Profile layer assembles correctly with profile data."""

    async def _profile_data(_user_id):
        return {
            "goals": ["build test"],
            "projects": ["test-project"],
            "preferences": {},
        }

    monkeypatch.setattr(prof, "get_user_profile", _profile_data)
    monkeypatch.setattr(prof, "count_tokens", lambda _text: 250)
    monkeypatch.setattr(prof, "trim_to_tokens", lambda _text, _limit: "trimmed-profile")

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )

    assert layer is not None
    assert layer.name == "user_profile"
    assert layer.tokens == 200  # trimmed to budget (raw content was 250 tokens)
    assert layer.content == "trimmed-profile"
    assert layer.metadata["type"] == "profile"
    assert layer.metadata["goals"] == 1
    assert layer.metadata["projects"] == 1


@pytest.mark.asyncio
async def test_assemble_profile_layer_trims_to_budget(monkeypatch):
    """Profile layer trims content when tokens exceed budget."""

    async def _profile_data(_user_id):
        return {"goals": ["build"], "projects": [], "preferences": {}}

    def _count_tokens(text):
        # Return small count to avoid auto-trim in the function
        return 50

    monkeypatch.setattr(prof, "get_user_profile", _profile_data)
    monkeypatch.setattr(prof, "count_tokens", _count_tokens)
    monkeypatch.setattr(prof, "trim_to_tokens", lambda _text, _limit: "trimmed")

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )

    # Since tokens (50) < budget (200), no trim should happen in the function
    # But the module level trim_to_tokens won't be called since tokens <= budget
    assert layer is not None
    assert layer.tokens == 50  # Not trimmed


@pytest.mark.asyncio
async def test_assemble_profile_layer_exception_handles_gracefully(monkeypatch):
    """Profile layer catches exceptions and returns None."""
    monkeypatch.setattr(prof, "get_user_profile", lambda _user_id: 1 / 0)

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )
    assert layer is None


@pytest.mark.asyncio
async def test_assemble_profile_layer_exception_on_format(monkeypatch):
    """Profile layer catches formatting exceptions and returns None."""

    async def _profile_data(_user_id):
        return {"goals": ["x"]}

    monkeypatch.setattr(prof, "get_user_profile", _profile_data)
    monkeypatch.setattr(prof, "format_user_profile", lambda _data: 1 / 0)

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )
    assert layer is None


@pytest.mark.asyncio
async def test_assemble_profile_layer_trims_content_to_budget(monkeypatch):
    """Profile layer trims content when tokens exceed budget."""

    async def _profile_data(_user_id):
        return {
            "goals": ["this is a longer goal that exceeds the budget limit"],
            "projects": [],
        }

    def _count_tokens(text):
        return 300  # Must exceed budget.profile_tokens

    monkeypatch.setattr(prof, "get_user_profile", _profile_data)
    monkeypatch.setattr(prof, "count_tokens", _count_tokens)
    monkeypatch.setattr(prof, "trim_to_tokens", lambda _text, _limit: "trimmed-content")

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )

    assert layer is not None
    assert layer.content == "trimmed-content"
    assert layer.tokens == 200  # Trimmed to budget


@pytest.mark.asyncio
async def test_assemble_profile_layer_empty_format_result(monkeypatch):
    """Profile layer returns None when format produces empty content."""

    async def _profile_data(_user_id):
        return {"goals": [], "projects": [], "preferences": {}}

    monkeypatch.setattr(prof, "get_user_profile", _profile_data)

    layer = await prof.assemble_profile_layer(
        user_id="user-1",
        remaining_tokens=500,
        budget=ContextBudget(profile_tokens=200),
    )
    assert layer is None  # No content to add
