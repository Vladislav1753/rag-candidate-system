import logging
from typing import Annotated, Any

import asyncpg
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)

from app.api.dependencies import (
    get_cache_service,
    get_db_pool,
    get_reranker,
)
from app.core.cache import CacheService
from app.middleware.rate_limit import (
    RATE_LIMIT_ONBOARDING,
    RATE_LIMIT_SEARCH,
    limiter,
)
from app.schemas.candidates import SearchRequest
from app.services.onboarding import (
    CandidateInput,
    CandidateOnboardingService,
)
from app.services.pipeline import process_candidate_background
from rag.reranker import RerankerService
from rag.retriever import search_candidates

logger = logging.getLogger(__name__)

candidates_router = APIRouter(prefix="/candidates", tags=["candidates"])


@candidates_router.post("/onboarding")
@limiter.limit(RATE_LIMIT_ONBOARDING)
async def onboard(
    request: Request,
    db_pool: Annotated[asyncpg.pool.Pool, Depends(get_db_pool)],
    data: CandidateInput,
    background_tasks: BackgroundTasks,
):
    service = CandidateOnboardingService(db_pool)
    result = await service.create_candidate(data)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))

    candidate_id = result["candidate_id"]

    background_tasks.add_task(process_candidate_background, candidate_id, data, db_pool)

    return {"status": "processing", "candidate_id": candidate_id}


@candidates_router.post("")
@limiter.limit(RATE_LIMIT_SEARCH)
async def search(
    request: Request,
    reranker: Annotated[RerankerService, Depends(get_reranker)],
    db_pool: Annotated[asyncpg.pool.Pool, Depends(get_db_pool)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    req: SearchRequest,
):
    filters: dict[str, Any] = {}
    if req.location:
        filters["location"] = req.location
    if req.min_experience:
        filters["min_experience"] = req.min_experience

    # Try to get cached results
    cached_results = await cache_service.get_cached_results(
        req.query, filters, req.top_k
    )
    if cached_results is not None:
        logger.info(f"Returning {len(cached_results)} cached results")
        return {"results": cached_results, "cached": True}

    # If not cached, perform search
    candidates = await search_candidates(
        query=req.query, filters=filters, db_pool=db_pool, top_k=req.top_k
    )

    logger.info(f"Database found {len(candidates)} candidates. Query: '{req.query}'")

    if not candidates:
        return {"results": [], "cached": False}

    results = []
    if req.query:
        try:
            ranked_results = reranker.rank_candidates(
                query=req.query, candidates=candidates, top_k=req.top_k
            )
            logger.info(f"Reranking complete. Returning {len(ranked_results)} results.")
            results = ranked_results
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            results = candidates[: req.top_k]
    else:
        results = candidates[: req.top_k]

    # Cache the results
    await cache_service.set_cached_results(req.query, filters, results)

    return {"results": results, "cached": False}
