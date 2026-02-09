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
        self.ttl = int(os.getenv("CACHE_TTL", "3600"))  # Default: 1 hour

    @staticmethod
    def _generate_cache_key(query: Optional[str], filters: Dict[str, Any]) -> str:
        """Generate a unique cache key based on query and filters."""
        cache_data = {
            "query": query or "",
            "filters": filters,
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"search:{hashlib.md5(cache_string.encode()).hexdigest()}"

    async def get_cached_results(
        self, query: Optional[str], filters: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached search results.

        Args:
            query: Search query string
            filters: Search filters

        Returns:
            Cached results or None if not found
        """
        try:
            cache_key = self._generate_cache_key(query, filters)
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                logger.info(f"Cache HIT for key: {cache_key}")
                return json.loads(cached_data)

            logger.info(f"Cache MISS for key: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None

    async def set_cached_results(
        self,
        query: Optional[str],
        filters: Dict[str, Any],
        results: List[Dict[str, Any]],
    ) -> bool:
        """
        Store search results in cache.

        Args:
            query: Search query string
            filters: Search filters
            results: Search results to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(query, filters)
            serialized_results = json.dumps(results, ensure_ascii=False)

            await self.redis.setex(cache_key, self.ttl, serialized_results)
            logger.info(
                f"Cached results for key: {cache_key} (TTL: {self.ttl}s, size: {len(results)} items)"
            )
            return True

        except Exception as e:
            logger.error(f"Cache storage error: {e}")
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

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        try:
            info = await self.redis.info("stats")

            search_keys = 0
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor, match="search:*", count=100
                )
                search_keys += len(keys)
                if cursor == 0:
                    break

            return {
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "search_keys_count": search_keys,
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / max(
                        info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
                    )
                    * 100
                ),
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
