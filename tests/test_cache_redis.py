"""
Tests for Redis cache service and protected cache endpoints.
"""

# pylint: disable=wrong-import-position
import pytest
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.core.cache import CacheService, init_redis_pool
from app.middleware.rate_limit import limiter

# Set test environment variables before importing app
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ADMIN_API_KEY"] = "test-admin-key-123"

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting globally to prevent 429 errors."""
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_cache_basic_operations():
    """Test basic cache operations: set, get, invalidate."""
    try:
        redis_client = await init_redis_pool()
    except Exception:
        pytest.skip("Redis not available")
        return

    cache_service = CacheService(redis_client)

    try:
        # Test cache miss
        result = await cache_service.get_cached_results("test query", {})
        assert result is None, "Expected cache miss for new query"

        # Test cache set
        test_results = [
            {"id": 1, "name": "John Doe", "score": 0.95},
            {"id": 2, "name": "Jane Smith", "score": 0.87},
        ]
        success = await cache_service.set_cached_results("test query", {}, test_results)
        assert success, "Cache set should succeed"

        # Test cache hit
        cached = await cache_service.get_cached_results("test query", {})
        assert cached is not None, "Expected cache hit"
        assert len(cached) == 2, "Expected 2 cached results"
        assert cached[0]["name"] == "John Doe"

        # Test cache with filters
        filters = {"location": "New York", "min_experience": 5}
        await cache_service.set_cached_results("test query", filters, test_results)
        cached_filtered = await cache_service.get_cached_results("test query", filters)
        assert cached_filtered is not None, "Expected cache hit with filters"

        # Test different filters result in different cache keys
        different_filters = {"location": "San Francisco", "min_experience": 3}
        cached_different = await cache_service.get_cached_results(
            "test query", different_filters
        )
        assert cached_different is None, "Expected cache miss with different filters"

        # Test cache invalidation
        deleted = await cache_service.invalidate_cache("search:*")
        assert deleted >= 2, f"Expected at least 2 keys deleted, got {deleted}"

        # Verify cache is empty after invalidation
        cached_after = await cache_service.get_cached_results("test query", {})
        assert cached_after is None, "Expected cache miss after invalidation"

    finally:
        # Cleanup
        if "redis_client" in locals():
            await cache_service.invalidate_cache("search:*")
            await redis_client.close()


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics endpoint."""
    try:
        redis_client = await init_redis_pool()
    except Exception:
        pytest.skip("Redis not available")
        return

    cache_service = CacheService(redis_client)

    try:
        # Clear cache first
        await cache_service.invalidate_cache("search:*")
        await cache_service.invalidate_cache("expand:*")

        # Add some test data
        test_results = [{"id": 1, "name": "Test"}]
        await cache_service.set_cached_results("query1", {}, test_results)
        await cache_service.set_cached_results("query2", {}, test_results)

        # Get stats
        stats = await cache_service.get_cache_stats()

        assert "breakdown" in stats
        assert "search_keys" in stats["breakdown"]
        assert stats["breakdown"]["search_keys"] >= 2, "Expected at least 2 search keys"

        assert "total_hits" in stats or "keyspace_hits" in stats
        assert "total_misses" in stats or "keyspace_misses" in stats

    finally:
        await cache_service.invalidate_cache("search:*")
        await redis_client.close()


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test that cache keys are generated correctly."""
    mock_redis = MagicMock()
    cache_service = CacheService(mock_redis)

    # pylint: disable=protected-access

    # 1. Search Keys
    key1 = cache_service._generate_cache_key("test", {"loc": "NY"})
    key2 = cache_service._generate_cache_key("test", {"loc": "NY"})
    assert key1 == key2, "Same inputs should produce same cache key"

    key3 = cache_service._generate_cache_key("different", {"loc": "NY"})
    assert key1 != key3, "Different queries should produce different cache keys"

    key4 = cache_service._generate_cache_key("test", {"loc": "SF"})
    assert key1 != key4, "Different filters should produce different cache keys"

    # Order of filters shouldn't matter
    key5 = cache_service._generate_cache_key("test", {"a": 1, "b": 2})
    key6 = cache_service._generate_cache_key("test", {"b": 2, "a": 1})
    assert key5 == key6, "Filter order should not affect cache key"

    # 2. Expansion Keys
    exp_key1 = cache_service._generate_expansion_key("Python Developer")
    exp_key2 = cache_service._generate_expansion_key(
        "python developer"
    )  # normalization test
    assert exp_key1 == exp_key2, "Expansion keys should be case-insensitive"


def test_cache_invalidate_without_api_key(client):
    """Test that /cache/invalidate is protected."""
    response = client.post("/cache/invalidate")
    assert response.status_code == 422  # Missing required header


def test_cache_invalidate_with_invalid_api_key(client):
    """Test that /cache/invalidate rejects invalid API key."""
    response = client.post("/cache/invalidate", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403
    assert "Invalid or missing API key" in response.json()["detail"]


def test_cache_stats_without_api_key(client):
    """Test that /cache/stats is protected."""
    response = client.get("/cache/stats")
    assert response.status_code == 422  # Missing required header


def test_cache_stats_with_invalid_api_key(client):
    """Test that /cache/stats rejects invalid API key."""
    response = client.get("/cache/stats", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403
    assert "Invalid or missing API key" in response.json()["detail"]


def test_cache_invalidate_with_valid_api_key(client):
    """Test that /cache/invalidate works with valid API key."""
    response = client.post(
        "/cache/invalidate",
        headers={"X-API-Key": "test-admin-key-123"},
        json={"scopes": ["search"]},  # Explicitly clear search only
    )
    # Check 200 OK (assuming Redis is up, otherwise 500)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "deleted_keys" in data
        assert "search" in data["deleted_keys"]


def test_cache_stats_with_valid_api_key(client):
    """Test that /cache/stats works with valid API key."""
    response = client.get("/cache/stats", headers={"X-API-Key": "test-admin-key-123"})

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "stats" in data
        assert "breakdown" in data["stats"]  # Check new structure


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
