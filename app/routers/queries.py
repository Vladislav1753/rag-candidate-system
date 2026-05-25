import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from app.api.dependencies import (
    get_cache_service,
    get_query_expander,
)
from app.core.cache import CacheService
from app.middleware.rate_limit import (
    RATE_LIMIT_DEFAULT,
    limiter,
)
from app.schemas.candidates import SearchRequest
from rag.agents.query_expansion_agent import QueryExpansionAgent

logger = logging.getLogger(__name__)

queries_router = APIRouter(prefix="/queries", tags=["queries"])


@queries_router.post("/expand")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def expand_query(
    request: Request,
    query_expander: Annotated[QueryExpansionAgent, Depends(get_query_expander)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    req: SearchRequest,
):
    """
    Expand a simple search query into a more detailed and comprehensive version.
    Example: 'python lead' -> 'Senior Python Developer, Team Lead, Django, Flask, Architecture'

    The expanded query is returned and can be used to update the SearchRequest.query field.
    """

    if not req.query or len(req.query.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Query must be at least 2 characters long"
        )

    cached_expansion = await cache_service.get_expanded_query(req.query)

    if cached_expansion:
        logger.info(f"Expansion Cache HIT: '{req.query}'")
        return {
            "status": "success",
            "original_query": req.query,
            "expanded_query": cached_expansion,
            "cached": True,
        }

    try:
        expanded_query = query_expander.expand_query(req.query)
        logger.info(f"Query expansion: '{req.query}' -> '{expanded_query}'")

        await cache_service.set_expanded_query(req.query, expanded_query)

        return {
            "status": "success",
            "original_query": req.query,
            "expanded_query": expanded_query,
            "cached": False,
        }
    except Exception as e:
        logger.error(f"Query expansion failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Query expansion failed: {str(e)}"
        ) from e
