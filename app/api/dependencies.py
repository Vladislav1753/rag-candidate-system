from collections.abc import Callable
from typing import TypeVar

import asyncpg
from fastapi import HTTPException, Request

from app.core.cache import CacheService
from rag.agents.query_expansion_agent import QueryExpansionAgent
from rag.reranker import RerankerService

T = TypeVar("T")


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
