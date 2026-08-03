"""
Pytest configuration and shared fixtures for API tests.
"""

import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
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
    try:
        importlib.import_module("api.sandbox_api")
    except Exception:
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
    _content_hash_cache: dict[str, bool] = {}
    _duplicate_prevented_count: int = 0
    _HASH_CACHE_MAX: int = 10_000

    async def embed_text(self, _text: str):
        return [0.0] * 1536

    async def embed_batch(self, texts):
        return [await self.embed_text(text) for text in texts]

    @classmethod
    def _check_and_register_hash(cls, content: str) -> bool:
        if content in cls._content_hash_cache:
            cls._duplicate_prevented_count += 1
            return True
        if len(cls._content_hash_cache) >= cls._HASH_CACHE_MAX:
            cls._content_hash_cache.pop(next(iter(cls._content_hash_cache)))
        cls._content_hash_cache[content] = True
        return False

    def get_dedup_stats(self):
        return {
            "duplicates_prevented": self._duplicate_prevented_count,
            "hash_cache_size": len(self._content_hash_cache),
        }

    async def store_message_embedding(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        content: str,
        metadata=None,
    ):
        from sqlalchemy import text as sa_text

        import api.services.embedding_service as module
        from api.storage.vector_models import EmbeddingModel

        async with module.get_db_context() as session:
            existing = await session.execute(
                sa_text(
                    "SELECT id FROM embeddings WHERE source_id = :sid AND user_id = :uid LIMIT 1"
                ),
                {"sid": message_id, "uid": user_id},
            )
            if existing.fetchone():
                return True

            embedding = await self.embed_text(content)
            session.add(
                EmbeddingModel(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    source_type="message",
                    source_id=message_id,
                    embedding=embedding,
                    content=content,
                    metadata_=metadata or {},
                )
            )
            if hasattr(session, "flush"):
                await session.flush()
        return True

    async def store_memory_fact(
        self,
        user_id: str,
        fact_text: str,
        category=None,
        metadata=None,
    ):
        import api.services.embedding_service as module
        from api.storage.vector_models import MemoryFactModel

        async with module.get_db_context() as session:
            session.add(
                MemoryFactModel(
                    user_id=user_id,
                    fact_text=fact_text,
                    category=category,
                    metadata_=metadata or {},
                )
            )
            if hasattr(session, "flush"):
                await session.flush()
        return True


class _AsyncEmbeddingWorkerStub:
    def __init__(self):
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.queue_message_embedding = AsyncMock()
        self.queue_summary_embedding = AsyncMock()
        self.queue_memory_embedding = AsyncMock()


async def _stub_db_context():  # pragma: no cover - compatibility shim
    raise RuntimeError("embedding service stub does not provide a DB context")


# Stub embedding service at module level so it's available at import time
# for all other test modules that chain through retrieval_service, etc.
if "api.services.embedding_service" not in sys.modules:
    _mock_providers = MagicMock()
    _mock_embedding = types.ModuleType("api.services.embedding_service")
    _mock_embedding.EmbeddingProviderUnavailableError = RuntimeError
    from api.storage.database import get_db_context as _real_get_db_context

    _mock_embedding.get_db_context = _real_get_db_context
    _mock_embedding.EmbeddingService = _EmbeddingServiceStub
    _mock_embedding.AsyncEmbeddingWorker = _AsyncEmbeddingWorkerStub
    _mock_embedding.embedding_worker = _AsyncEmbeddingWorkerStub()
    _mock_embedding.embedding_service = _EmbeddingServiceStub()
    sys.modules["api.services.providers"] = _mock_providers
    sys.modules["api.services.embedding_service"] = _mock_embedding


@pytest.fixture(scope="session", autouse=True)
def mock_embedding_service():
    """Ensure the embedding service stubs stay in place for the session."""
    yield
    sys.modules.pop("api.services.providers", None)
    sys.modules.pop("api.services.embedding_service", None)


# ---------------------------------------------------------------------------
# Shared yfinance stub — per-ticker data for all financial tests
# ---------------------------------------------------------------------------

_TICKER_DATA = {
    "AAPL": {
        "shortName": "Apple Inc.",
        "currentPrice": 150.0,
        "previousClose": 148.0,
        "regularMarketChange": 2.0,
        "regularMarketChangePercent": 1.35,
        "volume": 50_000_000,
        "regularMarketVolume": 50_000_000,
        "marketCap": 2_400_000_000_000,
        "currency": "USD",
        "exchange": "NMS",
        "totalRevenue": 400_000_000_000,
        "netIncomeToCommon": 100_000_000_000,
        "ebitda": 130_000_000_000,
        "grossProfits": 170_000_000_000,
        "operatingIncome": 120_000_000_000,
        "freeCashflow": 110_000_000_000,
        "operatingCashflow": 115_000_000_000,
        "totalCash": 60_000_000_000,
        "totalDebt": 110_000_000_000,
        "totalAssets": 350_000_000_000,
        "bookValue": 4.25,
        "sharesOutstanding": 15_600_000_000,
        "trailingPE": 28.5,
        "forwardPE": 25.0,
        "priceToBook": 35.0,
        "priceToSalesTrailing12Months": 6.0,
        "enterpriseToEbitda": 20.0,
        "enterpriseToRevenue": 6.5,
        "debtToEquity": 170.0,
        "currentRatio": 1.0,
        "returnOnEquity": 1.50,
        "returnOnAssets": 0.30,
        "profitMargins": 0.25,
        "operatingMargins": 0.30,
        "dividendYield": 0.005,
        "payoutRatio": 0.15,
        "beta": 1.25,
        "fiftyTwoWeekHigh": 200.0,
        "fiftyTwoWeekLow": 120.0,
        "trailingEps": 6.50,
        "forwardEps": 7.10,
        "pegRatio": 2.0,
        "earningsQuarterlyGrowth": 0.12,
        "revenueGrowth": 0.08,
    },
    "MSFT": {
        "shortName": "Microsoft Corp.",
        "currentPrice": 380.0,
        "previousClose": 375.0,
        "volume": 25_000_000,
        "marketCap": 2_800_000_000_000,
        "currency": "USD",
        "totalRevenue": 220_000_000_000,
        "netIncomeToCommon": 80_000_000_000,
        "ebitda": 100_000_000_000,
        "freeCashflow": 60_000_000_000,
        "operatingCashflow": 90_000_000_000,
        "totalCash": 100_000_000_000,
        "totalDebt": 60_000_000_000,
        "sharesOutstanding": 7_500_000_000,
        "trailingPE": 35.0,
        "forwardPE": 30.0,
        "priceToBook": 12.0,
        "enterpriseToEbitda": 25.0,
        "debtToEquity": 45.0,
        "returnOnEquity": 0.40,
        "returnOnAssets": 0.15,
        "profitMargins": 0.36,
        "dividendYield": 0.008,
        "beta": 0.95,
        "trailingEps": 10.80,
        "forwardEps": 12.00,
        "pegRatio": 2.5,
        "earningsQuarterlyGrowth": 0.20,
        "revenueGrowth": 0.12,
        "fiftyTwoWeekHigh": 420.0,
        "fiftyTwoWeekLow": 300.0,
    },
    "SPY": {
        "shortName": "SPDR S&P 500 ETF",
        "currentPrice": 500.0,
        "previousClose": 498.0,
        "volume": 80_000_000,
        "marketCap": 500_000_000_000,
        "currency": "USD",
        "trailingPE": 22.0,
        "dividendYield": 0.013,
        "beta": 1.0,
    },
}


class _FakeYfTicker:
    """Shared yfinance Ticker stub with per-ticker data."""

    def __init__(self, ticker: str):
        self._ticker = ticker
        base = _TICKER_DATA.get(ticker, _TICKER_DATA["AAPL"])
        self.info = dict(base)
        self.earnings_dates = None

    def history(self, period="1y", interval="1d"):
        import numpy as np
        import pandas as pd

        np.random.seed(hash(self._ticker) % 2**31)
        base_price = self.info.get("currentPrice", 150.0)
        n = 252
        changes = np.random.normal(0.0005, 0.015, n)
        prices = [base_price * 0.9]
        for c in changes:
            prices.append(prices[-1] * (1 + c))
        prices = prices[1:]

        dates = pd.bdate_range(end="2026-03-10", periods=n)
        df = pd.DataFrame(
            {
                "Open": [p * 0.999 for p in prices],
                "High": [p * 1.01 for p in prices],
                "Low": [p * 0.99 for p in prices],
                "Close": prices,
                "Volume": [int(50_000_000 * (0.8 + 0.4 * np.random.random())) for _ in prices],
            },
            index=dates,
        )
        return df


@pytest.fixture(scope="session", autouse=True)
def mock_yfinance():
    """Install a shared yfinance stub for all financial tests."""
    _yf_mod = types.ModuleType("yfinance")
    _yf_mod.Ticker = _FakeYfTicker  # type: ignore
    sys.modules["yfinance"] = _yf_mod
    yield
    sys.modules.pop("yfinance", None)


__all__ = ["_build_authenticated_client"]


# ---------------------------------------------------------------------------
# benchmark fixture fallback
# ---------------------------------------------------------------------------
# pytest-benchmark is an optional dependency (pip install goblin-assistant-api[benchmark]).
# When it is not installed the `benchmark` fixture is unavailable and the
# test_benchmarks.py suite would fail at collection time.  The stub below lets
# the tests run as plain assertions so the suite never hard-fails due to a
# missing plugin.  When pytest-benchmark IS installed its own fixture takes
# precedence via the normal pytest fixture resolution order.

try:
    import pytest_benchmark  # noqa: F401  # plugin registers its own fixture
except ImportError:

    @pytest.fixture
    def benchmark(request):
        """No-op stand-in for pytest-benchmark's fixture.

        Calls the function once and returns the result so tests pass without
        the plugin installed.  Install pytest-benchmark[histogram] to get
        real timing measurements.
        """

        def _run(func, *args, **kwargs):
            return func(*args, **kwargs)

        return _run


# ── Route inspection utilities ────────────────────────────────────────────────
# FastAPI 0.111+ / Starlette 0.40+ uses _IncludedRouter wrappers instead of
# flattening routes into app.routes. These helpers recursively walk the tree so
# tests don't break when include_router no longer mutates route paths.


def _collect_routes(router_or_app, prefix=""):
    """Recursively yield (full_path, method_set) for every APIRoute.

    Handles both pre- and post-0.111 FastAPI layouts:
    - Old: include_router flattens into APIRoute objects with full paths.
    - New: include_router stores _IncludedRouter wrappers (have .router + .prefix
      or .path) and Starlette Mount objects (have .routes + .path).
    """
    from fastapi.routing import APIRoute

    for item in getattr(router_or_app, "routes", []):
        if isinstance(item, APIRoute):
            yield (prefix + item.path, item.methods or set())
        else:
            # Prefer .prefix (set by include_router); fall back to .path (Mount).
            item_prefix = (
                getattr(item, "prefix", None) or getattr(item, "path", None) or ""
            )
            # _IncludedRouter exposes the wrapped router via .router; for Mount
            # the object itself has .routes, so fall back to item.
            sub_router = getattr(item, "router", item)
            if getattr(sub_router, "routes", None) is not None:
                yield from _collect_routes(sub_router, prefix + item_prefix)


def route_paths(router_or_app):
    """Return the set of all route paths in a FastAPI app/router."""
    return {path for path, _ in _collect_routes(router_or_app)}


def find_api_route(router_or_app, path_suffix, prefix=""):
    """Find the first APIRoute whose full path ends with *path_suffix*."""
    from fastapi.routing import APIRoute

    for item in getattr(router_or_app, "routes", []):
        if isinstance(item, APIRoute):
            if (prefix + item.path).endswith(path_suffix):
                return item
        else:
            item_prefix = (
                getattr(item, "prefix", None) or getattr(item, "path", None) or ""
            )
            sub_router = getattr(item, "router", item)
            if getattr(sub_router, "routes", None) is not None:
                found = find_api_route(sub_router, path_suffix, prefix + item_prefix)
                if found:
                    return found
    return None
