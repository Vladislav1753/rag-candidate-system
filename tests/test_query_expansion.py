"""
Tests for Query Expansion feature.
"""

# pylint: disable=wrong-import-position
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.cache import CacheService, init_redis_pool  # noqa: E402
from app.main import app  # noqa: E402
from app.middleware.rate_limit import limiter  # noqa: E402
from rag.agents.query_expansion_agent import QueryExpansionAgent  # noqa: E402


@pytest.mark.asyncio
async def test_query_expansion_agent_basic():
    """Test basic query expansion with mocked LLM."""
    with patch("rag.agents.query_expansion_agent.ChatOpenAI") as mock_llm_class:
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Senior Python Developer, Team Lead, Django, Flask, FastAPI, System Architecture"

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_class.return_value = mock_llm

        agent = QueryExpansionAgent()
        result = agent.expand_query("python lead")

        assert result is not None
        assert len(result) > len("python lead")
        assert "Python" in result or "python" in result.lower()


@pytest.mark.asyncio
async def test_query_expansion_agent_empty_query():
    """Test that empty queries are handled gracefully."""
    with patch("rag.agents.query_expansion_agent.ChatOpenAI"):
        agent = QueryExpansionAgent()
        # Empty string
        result = agent.expand_query("")
        assert result == ""
        # Whitespace
        result = agent.expand_query("   ")
        assert result == "   "
        # Too short
        result = agent.expand_query("a")
        assert result == "a"


@pytest.mark.asyncio
async def test_query_expansion_agent_removes_output_prefix():
    """Test that agent removes 'Output:' prefix if LLM adds it."""
    with patch("rag.agents.query_expansion_agent.ChatOpenAI") as mock_llm_class:
        mock_response = MagicMock()
        mock_response.content = "Output: Senior Python Developer, Django, Flask"
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_class.return_value = mock_llm

        agent = QueryExpansionAgent()
        result = agent.expand_query("python dev")
        assert not result.startswith("Output:")
        assert "Python" in result or "python" in result.lower()


@pytest.mark.asyncio
async def test_expansion_cache_operations():
    """Test caching of expanded queries (Integration Test with Redis)."""
    # This test assumes a local Redis is running.
    # If not available, it might fail or should be skipped.
    try:
        redis_client = await init_redis_pool()
    except Exception:
        pytest.skip("Redis not available")
        return

    cache_service = CacheService(redis_client)
    try:
        original_query = "react frontend"
        expanded_query = "Frontend Developer, React, JavaScript, TypeScript, Next.js"

        # Cleanup before test
        await cache_service.invalidate_cache("expand:*")

        # Test cache miss
        cached = await cache_service.get_expanded_query(original_query)
        assert cached is None, "Expected cache miss for new query"

        # Test cache set
        success = await cache_service.set_expanded_query(original_query, expanded_query)
        assert success, "Cache set should succeed"

        # Test cache hit
        cached = await cache_service.get_expanded_query(original_query)
        assert cached is not None, "Expected cache hit"
        assert cached == expanded_query

        # Test case-insensitive caching
        cached_upper = await cache_service.get_expanded_query("REACT FRONTEND")
        assert cached_upper is not None
        assert cached_upper == expanded_query
    finally:
        await redis_client.close()


@pytest.mark.asyncio
async def test_expansion_endpoint_success(expander_mock, cache_mock):
    """Test /expand-query endpoint with valid request."""
    client = TestClient(app)

    mock_expander = expander_mock

    mock_expander.expand_query.return_value = (
        "Senior Data Scientist, Python, Machine Learning, TensorFlow"
    )

    response = client.post("/expand-query", json={"query": "data scientist"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["original_query"] == "data scientist"
    assert "expanded_query" in data


@pytest.mark.asyncio
async def test_expansion_endpoint_empty_query(expander_mock, cache_mock):
    """Test /expand-query endpoint with empty query."""
    client = TestClient(app)

    response = client.post("/expand-query", json={"query": ""})
    assert response.status_code == 400
    assert "at least 2 characters" in response.json()["detail"]


@pytest.mark.asyncio
async def test_expansion_endpoint_short_query(expander_mock, cache_mock):
    """Test /expand-query endpoint with too short query."""
    client = TestClient(app)

    response = client.post("/expand-query", json={"query": "a"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_expansion_endpoint_with_cache(expander_mock, cache_mock):
    """Test that expansion endpoint uses cache."""
    client = TestClient(app)

    mock_expander = expander_mock
    mock_cache = cache_mock
    mock_expander.expand_query.return_value = "Expanded Query"

    response = client.post("/expand-query", json={"query": "devops aws"})
    assert response.status_code == 200
    assert response.json()["cached"] is False

    # --- Case 2: Cache Hit ---
    mock_cache.get_expanded_query = AsyncMock(
        return_value="Senior DevOps Engineer, AWS, Docker, Kubernetes"
    )

    response = client.post("/expand-query", json={"query": "devops aws"})
    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert data["expanded_query"] == "Senior DevOps Engineer, AWS, Docker, Kubernetes"


@pytest.mark.asyncio
async def test_expansion_endpoint_with_filters(expander_mock, cache_mock):
    """Test that expansion endpoint accepts SearchRequest with filters."""
    client = TestClient(app)

    mock_expander = expander_mock

    mock_expander.expand_query.return_value = "Senior Python Developer, Django, Flask"

    response = client.post(
        "/expand-query",
        json={
            "query": "python",
            "location": "New York",
            "min_experience": 5,
            "top_k": 10,
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_expansion_cache_invalidation():
    """Test that expansion cache can be invalidated (Integration)."""
    try:
        redis_client = await init_redis_pool()
    except Exception:
        pytest.skip("Redis not available")
        return

    cache_service = CacheService(redis_client)
    try:
        await cache_service.set_expanded_query("python", "Senior Python Developer")
        await cache_service.set_expanded_query("java", "Senior Java Developer")

        deleted_count = await cache_service.invalidate_cache("expand:*")
        assert deleted_count >= 2

        assert await cache_service.get_expanded_query("python") is None
    finally:
        await redis_client.close()


@pytest.mark.asyncio
async def test_expansion_rate_limiting(expander_mock, cache_mock):
    """Test that expansion endpoint has rate limiting."""
    limiter.enabled = True

    client = TestClient(app)

    mock_expander = expander_mock
    mock_expander.expand_query.return_value = "Expanded"

    # Make multiple requests
    responses = []
    for i in range(25):  # Rate limit is 20/hour
        response = client.post("/expand-query", json={"query": f"test query {i}"})
        responses.append(response.status_code)

    assert 429 in responses, "Expected at least one request to be rate limited"


@pytest.mark.asyncio
async def test_expansion_key_generation_consistency():
    """Test that expansion cache keys are generated consistently."""
    # pylint: disable=protected-access
    # Use MagicMock instead of real Redis connection
    mock_redis = MagicMock()
    service = CacheService(mock_redis)

    key1 = service._generate_expansion_key("python developer")
    key2 = service._generate_expansion_key("python developer")
    assert key1 == key2

    key3 = service._generate_expansion_key("PYTHON DEVELOPER")
    key4 = service._generate_expansion_key("Python Developer")
    assert key3 == key4

    key5 = service._generate_expansion_key("  python developer  ")
    key6 = service._generate_expansion_key("python developer")
    assert key5 == key6
