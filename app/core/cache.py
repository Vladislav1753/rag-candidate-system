"""
Redis cache service for search results.
"""
import json
import logging
from typing import Optional, Dict, Any, List
import redis.asyncio as redis
import os
import hashlib

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for search results."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = int(os.getenv("CACHE_TTL", "86400"))  # Default: 24 hours

    def _generate_cache_key(self, query: Optional[str], filters: Dict[str, Any]) -> str:
        """Generate a unique cache key based on query and filters."""
        cache_data = {
            "query": query or "",
            "filters": filters,
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"search:{hashlib.md5(cache_string.encode()).hexdigest()}"

    def _generate_expansion_key(self, query: str) -> str:
        """Generate a unique cache key for expansion queries."""
        normalized = query.strip().lower()
        return f"expand:{hashlib.md5(normalized.encode()).hexdigest()}"

    async def get_cached_results(
        self, query: Optional[str], filters: Dict[str, Any], top_k: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached search results.

        Args:
            query: Search query string
            filters: Search filters
            top_k: Number of results requested

        Returns:
            Sliced cached results or None if cache miss or insufficient results
        """
        try:
            cache_key = self._generate_cache_key(query, filters)
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                cached_list = json.loads(cached_data)
                if len(cached_list) >= top_k:
                    logger.info(
                        f"Cache HIT for key: {cache_key} ({len(cached_list)} cached, returning {top_k})"
                    )
                    return cached_list[:top_k]
                logger.info(
                    f"Cache MISS (insufficient): {len(cached_list)} cached < {top_k} requested"
                )
                return None

            logger.info(f"Cache MISS for key: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None

    async def get_expanded_query(self, query: str) -> Optional[str]:
        """Get cached expanded query string.

        Args:
            query: Original search query string

        Returns:
            Cached expanded query or None if not found
        """
        try:
            key = self._generate_expansion_key(query)
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Expansion cache get error: {e}")
            return None

    async def set_cached_results(
        self,
        query: Optional[str],
        filters: Dict[str, Any],
        results: List[Dict[str, Any]],
    ) -> bool:
        """
        Store search results in cache. Never downgrades an existing larger result set.

        Args:
            query: Search query string
            filters: Search filters
            results: Search results to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(query, filters)

            existing = await self.redis.get(cache_key)
            if existing:
                existing_list = json.loads(existing)
                if len(existing_list) >= len(results):
                    logger.info(
                        f"Skipping cache write: existing {len(existing_list)} >= new {len(results)}"
                    )
                    return True

            serialized_results = json.dumps(results, ensure_ascii=False)

            await self.redis.setex(cache_key, self.ttl, serialized_results)
            logger.info(
                f"Cached results for key: {cache_key} (TTL: {self.ttl}s, size: {len(results)} items)"
            )
            return True

        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False

    async def set_expanded_query(self, query: str, expanded_value: str) -> bool:
        """Cache the expanded query string.

        Args:
            query: Original search query string
            expanded_value: Expanded query string to cache
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._generate_expansion_key(query)
            await self.redis.setex(key, self.ttl, expanded_value)
            return True
        except Exception as e:
            logger.error(f"Expansion cache set error: {e}")
            return False

    async def invalidate_cache(self, pattern: str = "search:*") -> int:
        """
        Invalidate cache by pattern.

        Args:
            pattern: Redis key pattern to delete

        Returns:
            Number of keys deleted
        """
        try:
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor, match=pattern, count=100
                )
                if keys:
                    deleted = await self.redis.delete(*keys)
                    deleted_count += deleted

                if cursor == 0:
                    break

            logger.info(f"Invalidated {deleted_count} cache keys matching '{pattern}'")
            return deleted_count

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def _count_keys(self, pattern: str) -> int:
        """Helper to count keys by pattern.

        Args:
            pattern: Redis key pattern to count
        Returns:
            Total number of keys matching the pattern
        """
        count = 0
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor, match=pattern, count=100
            )
            count += len(keys)
            if cursor == 0:
                break
        return count

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        try:
            info = await self.redis.info("stats")

            search_keys = await self._count_keys("search:*")
            expand_keys = await self._count_keys("expand:*")

            total_hits = info.get("keyspace_hits", 0)
            total_misses = info.get("keyspace_misses", 0)

            return {
                "redis_total_commands": info.get("total_commands_processed", 0),
                "total_hits": total_hits,
                "total_misses": total_misses,
                "hit_rate": (
                    (total_hits / (total_hits + total_misses) * 100)
                    if (total_hits + total_misses) > 0
                    else 0
                ),
                "breakdown": {
                    "search_keys": search_keys,
                    "expand_keys": expand_keys,
                    "total_rag_keys": search_keys + expand_keys,
                },
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}


async def init_redis_pool() -> redis.Redis:
    """Initialize Redis connection pool."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        # Test connection
        await redis_client.ping()
        logger.info(f"Connected to Redis at {redis_url}")
        return redis_client

    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
