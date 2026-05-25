import os
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-123")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_cache_service, get_query_expander  # noqa: E402
from app.core.cache import CacheService, init_redis_pool  # noqa: E402
from app.main import app  # noqa: E402
from app.middleware.rate_limit import limiter  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def expander_mock():
    mock_expander = MagicMock()
    mock_expander.expand_query.return_value = "Expanded Query"

    app.dependency_overrides[get_query_expander] = lambda: mock_expander

    yield mock_expander

    app.dependency_overrides.clear()


@pytest.fixture
def cache_mock():
    mock_cache = MagicMock()
    mock_cache.get_expanded_query = AsyncMock(return_value=None)
    mock_cache.set_expanded_query = AsyncMock(return_value=True)
    mock_cache.invalidate_cache = AsyncMock(return_value=0)
    mock_cache.get_cache_stats = AsyncMock(return_value={"breakdown": {}})

    app.dependency_overrides[get_cache_service] = lambda: mock_cache

    yield mock_cache

    app.dependency_overrides.clear()


@pytest.fixture
async def cache_service():
    try:
        redis_client = await init_redis_pool()
    except Exception:
        pytest.skip("Redis not available")

    service = CacheService(redis_client)

    try:
        yield service
    finally:
        await service.invalidate_cache("search:*")
        await service.invalidate_cache("expand:*")
        await redis_client.close()


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """
    Disable rate limiting globally for all tests to prevent 429 errors
    during functional testing.
    """
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)
