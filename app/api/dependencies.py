import logging
import secrets
from collections.abc import Callable
from typing import TypeVar

import asyncpg
from fastapi import (
    Header,
    HTTPException,
    Request,
)

from app.core.cache import CacheService
from app.core.config import settings
from rag.agents.query_expansion_agent import QueryExpansionAgent
from rag.reranker import RerankerService

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def verify_admin(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Verify admin API key for protected endpoints.
    Uses secrets.compare_digest to prevent timing attacks.
    """
    if not settings.app.admin_api_key:
        logger.error("ADMIN_API_KEY is not configured")
        raise HTTPException(status_code=500, detail="Admin API key is not configured")

    if not secrets.compare_digest(x_api_key, settings.app.admin_api_key):
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return x_api_key


def get_app_state_resource(
    state_key: str, resource_type: type[T]
) -> Callable[[Request], T]:
    def _dependency_provider(request: Request) -> T:
        resource = getattr(request.app.state, state_key, None)
        if resource is None:
            raise HTTPException(
                status_code=500,
                detail=f"Resource '{state_key}' not initialized in app state",
            )
        return resource

    return _dependency_provider


get_db_pool = get_app_state_resource("db_pool", asyncpg.pool.Pool)
get_cache_service = get_app_state_resource("cache_service", CacheService)
get_reranker = get_app_state_resource("reranker", RerankerService)
get_query_expander = get_app_state_resource("query_expander", QueryExpansionAgent)
