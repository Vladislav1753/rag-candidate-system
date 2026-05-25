from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
)

from app.api.dependencies import (
    get_cache_service,
    verify_admin,
)
from app.core.cache import CacheService
from app.schemas.cache import InvalidateCacheRequest

cache_router = APIRouter(prefix="/cache", tags=["cache"])


@cache_router.delete("", dependencies=[Depends(verify_admin)])
async def invalidate(
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    req: InvalidateCacheRequest = InvalidateCacheRequest(),
):
    """
    Invalidate cache.
    By default, invalidates ALL caches.
    To invalidate specific parts, pass a JSON body: {"scopes": ["search"]}
    Requires admin API key.
    """

    results = {"search": 0, "expanded_queries": 0, "total": 0}

    if "search" in req.scopes:
        deleted = await cache_service.invalidate_cache("search:*")
        results["search"] = deleted

    if "expand" in req.scopes:
        deleted = await cache_service.invalidate_cache("expand:*")
        results["expanded_queries"] = deleted

    results["total"] = results["search"] + results["expanded_queries"]

    return {"status": "success", "deleted_keys": results}


@cache_router.get("/stats", dependencies=[Depends(verify_admin)])
async def get_stats(
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
):
    """Get cache statistics. Requires admin API key."""

    stats = await cache_service.get_cache_stats()
    return {"status": "success", "stats": stats}
