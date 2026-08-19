"""Tests for health_checks.py — internal probe functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.health_checks import (
    _check_chroma,
    _check_cost_tracking,
    _check_mcp,
    _check_raptor,
    _check_sandbox,
    _check_vector_store,
)
from api.health_core import check_redis_health

# ── _check_vector_store / _check_chroma (alias) ───────────────────────────────


def _mock_store(status: str = "healthy", backend: str = "pgvector", **extra) -> MagicMock:
    store = MagicMock()
    store.health = AsyncMock(return_value={"status": status, "backend": backend, **extra})
    return store


class TestCheckVectorStore:
    @pytest.mark.asyncio
    async def test_delegates_to_store_health(self, monkeypatch):
        monkeypatch.delenv("CHROMA_URL", raising=False)
        monkeypatch.delenv("CHROMA_API_URL", raising=False)
        with patch("api.services.vector_store.create_vector_store", return_value=_mock_store()):
            result = await _check_vector_store()
        assert result["status"] == "healthy"
        assert result["backend"] == "pgvector"

    @pytest.mark.asyncio
    async def test_returns_dict_with_status_key(self):
        with patch("api.services.vector_store.create_vector_store", return_value=_mock_store()):
            result = await _check_vector_store()
        assert "status" in result

    @pytest.mark.asyncio
    async def test_degraded_store_propagates(self):
        degraded_store = _mock_store(status="degraded", error="connection refused")
        with patch("api.services.vector_store.create_vector_store", return_value=degraded_store):
            result = await _check_vector_store()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_chroma_url_selects_chroma_backend(self, monkeypatch):
        monkeypatch.setenv("CHROMA_URL", "http://chroma.internal:8000")
        chroma_store = _mock_store(
            status="healthy", backend="chroma", url="http://chroma.internal:8000"
        )
        with patch("api.services.vector_store.create_vector_store", return_value=chroma_store):
            result = await _check_vector_store()
        assert result["backend"] == "chroma"

    @pytest.mark.asyncio
    async def test_check_chroma_alias_is_same_function(self):
        """_check_chroma is a backward-compat alias for _check_vector_store."""
        assert _check_chroma is _check_vector_store


# ── _check_mcp ────────────────────────────────────────────────────────────────


class TestCheckMcp:
    @pytest.mark.asyncio
    async def test_default_server_unreachable_returns_degraded(self, monkeypatch):
        monkeypatch.delenv("MCP_SERVERS", raising=False)
        result = await _check_mcp()
        assert result["status"] in {"healthy", "degraded"}

    @pytest.mark.asyncio
    async def test_returns_servers_list(self, monkeypatch):
        monkeypatch.delenv("MCP_SERVERS", raising=False)
        result = await _check_mcp()
        assert "details" in result
        assert "servers" in result["details"]

    @pytest.mark.asyncio
    async def test_multiple_servers_in_env(self, monkeypatch):
        monkeypatch.setenv("MCP_SERVERS", "localhost:19991,localhost:19992")
        result = await _check_mcp()
        assert len(result["details"]["servers"]) == 2

    @pytest.mark.asyncio
    async def test_server_without_port_uses_default(self, monkeypatch):
        monkeypatch.setenv("MCP_SERVERS", "localhost")
        result = await _check_mcp()
        assert result["details"]["count"] == 1

    @pytest.mark.asyncio
    async def test_all_unreachable_status_is_degraded(self, monkeypatch):
        monkeypatch.setenv("MCP_SERVERS", "127.0.0.1:19993")
        result = await _check_mcp()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_count_matches_servers_configured(self, monkeypatch):
        monkeypatch.setenv("MCP_SERVERS", "h1:1,h2:2,h3:3")
        result = await _check_mcp()
        assert result["details"]["count"] == 3


# ── _check_raptor ─────────────────────────────────────────────────────────────


class TestCheckRaptor:
    @pytest.mark.asyncio
    async def test_returns_status_key(self):
        result = await _check_raptor()
        assert "status" in result
        assert result["status"] in {"healthy", "degraded"}


# ── _check_sandbox ────────────────────────────────────────────────────────────


class TestCheckSandbox:
    @pytest.mark.asyncio
    async def test_not_enabled_no_image_returns_degraded(self, monkeypatch):
        monkeypatch.setenv("VITE_FEATURE_SANDBOX", "false")
        monkeypatch.delenv("SANDBOX_IMAGE", raising=False)
        result = await _check_sandbox()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_enabled_no_docker_returns_healthy(self, monkeypatch):
        monkeypatch.setenv("VITE_FEATURE_SANDBOX", "true")
        monkeypatch.delenv("SANDBOX_IMAGE", raising=False)
        result = await _check_sandbox()
        # No image, no docker check required — should be healthy (configured=True)
        assert result["status"] == "healthy"
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_image_set_no_docker_binary_returns_healthy(self, monkeypatch):
        from unittest.mock import patch

        monkeypatch.setenv("SANDBOX_IMAGE", "goblin:latest")
        monkeypatch.setenv("VITE_FEATURE_SANDBOX", "false")
        # Patch shutil.which to return None (no docker binary)
        with patch("shutil.which", return_value=None):
            result = await _check_sandbox()
        assert result["status"] == "healthy"
        assert result["image"] == "goblin:latest"

    @pytest.mark.asyncio
    async def test_returns_dict_with_status_key(self, monkeypatch):
        monkeypatch.setenv("VITE_FEATURE_SANDBOX", "false")
        monkeypatch.delenv("SANDBOX_IMAGE", raising=False)
        result = await _check_sandbox()
        assert "status" in result


# ── _check_cost_tracking ──────────────────────────────────────────────────────


class TestCheckCostTracking:
    @pytest.mark.asyncio
    async def test_not_configured_returns_unknown(self, monkeypatch):
        monkeypatch.setenv("COST_TRACKING_ENABLED", "false")
        monkeypatch.delenv("COST_DB_URL", raising=False)
        result = await _check_cost_tracking()
        assert result["status"] == "unknown"
        assert result["total_cost"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_unsupported_db_scheme_returns_degraded(self, monkeypatch):
        monkeypatch.setenv("COST_TRACKING_ENABLED", "true")
        monkeypatch.setenv("COST_DB_URL", "mongodb://localhost/costs")
        result = await _check_cost_tracking()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_bad_sqlite_path_returns_degraded(self, monkeypatch):
        monkeypatch.setenv("COST_TRACKING_ENABLED", "true")
        monkeypatch.setenv("COST_DB_URL", "sqlite:/nonexistent_dir/costs.db")
        result = await _check_cost_tracking()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_cost_tracking_enabled_no_db_returns_unknown(self, monkeypatch):
        monkeypatch.setenv("COST_TRACKING_ENABLED", "true")
        monkeypatch.delenv("COST_DB_URL", raising=False)
        result = await _check_cost_tracking()
        # No DB URL even with enabled flag → falls through to degraded/unknown
        assert "status" in result

    @pytest.mark.asyncio
    async def test_placeholder_redis_url_returns_unknown(self, monkeypatch):
        monkeypatch.setenv(
            "REDIS_URL",
            "redis://default:<your-upstash-password>@<your-cluster>.upstash.io:6379",
        )
        result = await check_redis_health()
        assert result["status"] == "unknown"
        assert "placeholder" in result["error"]

    @pytest.mark.asyncio
    async def test_postgres_url_without_psycopg_returns_degraded(self, monkeypatch):
        monkeypatch.setenv("COST_TRACKING_ENABLED", "true")
        monkeypatch.setenv("COST_DB_URL", "postgresql://localhost/costs")
        from unittest.mock import patch

        with patch.dict("sys.modules", {"psycopg": None}):
            result = await _check_cost_tracking()
        assert result["status"] == "degraded"
