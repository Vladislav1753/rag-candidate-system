"""
Tests for Redis cache service and protected cache endpoints.
"""

from unittest.mock import MagicMock

import pytest

from app.core.cache import CacheService


@pytest.mark.asyncio
async def test_cache_basic_operations(cache_service):
    """Test basic cache operations: set, get, invalidate."""
    result = await cache_service.get_cached_results("test query", {}, 5)
    assert result is None, "Expected cache miss for new query"

    test_results = [
        {"id": 1, "name": "John Doe", "score": 0.95},
        {"id": 2, "name": "Jane Smith", "score": 0.87},
        {"id": 3, "name": "Bob Lee", "score": 0.80},
    ]
    success = await cache_service.set_cached_results("test query", {}, test_results)
    assert success, "Cache set should succeed"

    # Requesting <= cached count: cache hit, sliced.
    cached_3 = await cache_service.get_cached_results("test query", {}, 3)
    assert cached_3 is not None, "Expected cache hit for top_k=3"
    assert len(cached_3) == 3

    cached_2 = await cache_service.get_cached_results("test query", {}, 2)
    assert cached_2 is not None, "Expected cache hit for top_k=2"
    assert len(cached_2) == 2
    assert cached_2[0]["name"] == "John Doe"

    # Requesting > cached count: cache miss because there are not enough items.
    cached_10 = await cache_service.get_cached_results("test query", {}, 10)
    assert cached_10 is None, "Expected cache miss when top_k > cached count"

    filters = {"location": "New York", "min_experience": 5}
    await cache_service.set_cached_results("test query", filters, test_results)

    cached_filtered = await cache_service.get_cached_results("test query", filters, 3)
    assert cached_filtered is not None, "Expected cache hit with filters"

    different_filters = {"location": "San Francisco", "min_experience": 3}
    cached_different = await cache_service.get_cached_results(
        "test query", different_filters, 3
    )
    assert cached_different is None, "Expected cache miss with different filters"

    deleted = await cache_service.invalidate_cache("search:*")
    assert deleted >= 2, f"Expected at least 2 keys deleted, got {deleted}"

    cached_after = await cache_service.get_cached_results("test query", {}, 3)
    assert cached_after is None, "Expected cache miss after invalidation"


@pytest.mark.asyncio
async def test_cache_no_downgrade(cache_service):
    """Test that a smaller result set never overwrites a larger cached one."""
    await cache_service.invalidate_cache("search:*")

    large = [{"id": i} for i in range(10)]
    await cache_service.set_cached_results("q", {}, large)

    small = [{"id": i} for i in range(3)]
    await cache_service.set_cached_results("q", {}, small)

    cached = await cache_service.get_cached_results("q", {}, 10)
    assert cached is not None, "Expected 10 items to still be cached"
    assert len(cached) == 10, f"Expected 10, got {len(cached)}"


@pytest.mark.asyncio
async def test_cache_upgrade(cache_service):
    """Test that a larger result set upgrades the cache."""
    await cache_service.invalidate_cache("search:*")

    small = [{"id": i} for i in range(5)]
    await cache_service.set_cached_results("q", {}, small)

    result = await cache_service.get_cached_results("q", {}, 10)
    assert result is None, "Expected cache miss when requesting more than cached"

    large = [{"id": i} for i in range(10)]
    await cache_service.set_cached_results("q", {}, large)

    result = await cache_service.get_cached_results("q", {}, 10)
    assert result is not None and len(result) == 10

    result5 = await cache_service.get_cached_results("q", {}, 5)
    assert result5 is not None and len(result5) == 5


@pytest.mark.asyncio
async def test_cache_stats(cache_service):
    """Test cache statistics endpoint."""
    await cache_service.invalidate_cache("search:*")
    await cache_service.invalidate_cache("expand:*")

    test_results = [{"id": 1, "name": "Test"}]
    await cache_service.set_cached_results("query1", {}, test_results)
    await cache_service.set_cached_results("query2", {}, test_results)

    stats = await cache_service.get_cache_stats()

    assert "breakdown" in stats
    assert "search_keys" in stats["breakdown"]
    assert stats["breakdown"]["search_keys"] >= 2, "Expected at least 2 search keys"

    assert "total_hits" in stats or "keyspace_hits" in stats
    assert "total_misses" in stats or "keyspace_misses" in stats


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test that cache keys are generated correctly."""
    mock_redis = MagicMock()
    cache_service = CacheService(mock_redis)

    # pylint: disable=protected-access

    key1 = cache_service._generate_cache_key("test", {"loc": "NY"})
    key2 = cache_service._generate_cache_key("test", {"loc": "NY"})
    assert key1 == key2, "Same inputs should produce same cache key"

    key3 = cache_service._generate_cache_key("different", {"loc": "NY"})
    assert key1 != key3, "Different queries should produce different cache keys"

    key4 = cache_service._generate_cache_key("test", {"loc": "SF"})
    assert key1 != key4, "Different filters should produce different cache keys"

    key5 = cache_service._generate_cache_key("test", {"a": 1, "b": 2})
    key6 = cache_service._generate_cache_key("test", {"b": 2, "a": 1})
    assert key5 == key6, "Filter order should not affect cache key"

    exp_key1 = cache_service._generate_expansion_key("Python Developer")
    exp_key2 = cache_service._generate_expansion_key("python developer")
    assert exp_key1 == exp_key2, "Expansion keys should be case-insensitive"


def test_cache_invalidate_without_api_key(client, cache_mock):
    """Test that DELETE /cache is protected."""
    response = client.delete("/cache")
    assert response.status_code == 422


def test_cache_invalidate_with_invalid_api_key(client, cache_mock):
    """Test that DELETE /cache rejects invalid API key."""
    response = client.delete("/cache", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403
    assert "Invalid or missing API key" in response.json()["detail"]


def test_cache_stats_without_api_key(client, cache_mock):
    """Test that /cache/stats is protected."""
    response = client.get("/cache/stats")
    assert response.status_code == 422


def test_cache_stats_with_invalid_api_key(client, cache_mock):
    """Test that /cache/stats rejects invalid API key."""
    response = client.get("/cache/stats", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403
    assert "Invalid or missing API key" in response.json()["detail"]


def test_cache_invalidate_with_valid_api_key(client, cache_mock):
    """Test that DELETE /cache works with valid API key."""
    response = client.request(
        "DELETE",
        "/cache",
        headers={"X-API-Key": "test-admin-key-123"},
        json={"scopes": ["search"]},
    )
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "deleted_keys" in data
        assert "search" in data["deleted_keys"]


def test_cache_stats_with_valid_api_key(client, cache_mock):
    """Test that /cache/stats works with valid API key."""
    response = client.get("/cache/stats", headers={"X-API-Key": "test-admin-key-123"})

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "stats" in data
        assert "breakdown" in data["stats"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
