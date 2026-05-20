import logging
import secrets
import sys
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded

from app.core.cache import CacheService, init_redis_pool
from app.core.config import settings
from app.middleware.rate_limit import (
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_EXTRACT,
    RATE_LIMIT_ONBOARDING,
    RATE_LIMIT_SEARCH,
    limiter,
    rate_limit_exceeded_handler,
)
from app.services.onboarding import (
    CandidateInput,
    CandidateOnboardingService,
    init_db_pool,
)
from app.services.parser import extract_text_from_pdf
from app.services.pipeline import process_candidate_background
from rag.agents.query_expansion_agent import QueryExpansionAgent
from rag.onboarding_graph import app_workflow
from rag.reranker import RerankerService
from rag.retriever import search_candidates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")

db_pool = None
reranker = None
redis_client = None
cache_service = None
query_expander = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, reranker, redis_client, cache_service, query_expander
    logger.info("Connecting to Database...")
    db_pool = await init_db_pool()

    logger.info("Connecting to Redis...")
    redis_client = await init_redis_pool()
    cache_service = CacheService(redis_client)

    logger.info("Loading Reranker model (CrossEncoder)...")
    reranker = RerankerService()

    logger.info("Initializing Query Expansion Agent...")
    query_expander = QueryExpansionAgent()

    yield
    if db_pool:
        logger.info("Closing Database connection...")
        await db_pool.close()
    if redis_client:
        logger.info("Closing Redis connection...")
        await redis_client.close()


app = FastAPI(lifespan=lifespan)

# Add rate limiter state to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class SearchRequest(BaseModel):
    query: str | None = None
    location: str | None = None
    min_experience: int | None = None
    top_k: int = 5


class InvalidateCacheRequest(BaseModel):
    scopes: list[Literal["search", "expand"]] = ["search", "expand"]


@app.post("/extract")
@limiter.limit(RATE_LIMIT_EXTRACT)
async def extract_from_pdf(request: Request, file: UploadFile = File(...)):
    logger.info(f"Receiving file: {file.filename}")

    try:
        raw_text = extract_text_from_pdf(file.file)
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid PDF file") from e

    if not raw_text or len(raw_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="PDF text is too short or empty.")

    try:
        result = app_workflow.invoke({"raw_text": raw_text})

        return {
            "status": "success",
            "extracted_data": result.get("extracted_data", {}),
            "final_summary": result.get("final_summary", ""),
        }
    except Exception as e:
        logger.error(f"Extraction workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/onboarding")
@limiter.limit(RATE_LIMIT_ONBOARDING)
async def onboard_candidate(
    request: Request, data: CandidateInput, background_tasks: BackgroundTasks
):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    service = CandidateOnboardingService(db_pool)
    result = await service.create_candidate(data)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))

    candidate_id = result["candidate_id"]

    background_tasks.add_task(process_candidate_background, candidate_id, data, db_pool)

    return {"status": "processing", "candidate_id": candidate_id}


@app.post("/expand-query")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def expand_query_endpoint(request: Request, req: SearchRequest):
    """
    Expand a simple search query into a more detailed and comprehensive version.
    Example: 'python lead' -> 'Senior Python Developer, Team Lead, Django, Flask, Architecture'

    The expanded query is returned and can be used to update the SearchRequest.query field.
    """
    if not query_expander:
        raise HTTPException(status_code=500, detail="Query expander not initialized")

    if not cache_service:
        raise HTTPException(status_code=500, detail="Cache service not initialized")

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


@app.post("/search")
@limiter.limit(RATE_LIMIT_SEARCH)
async def search_endpoint(request: Request, req: SearchRequest):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    if not reranker:
        raise HTTPException(status_code=500, detail="Reranker not initialized")

    if not cache_service:
        raise HTTPException(status_code=500, detail="Cache service not initialized")

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


@app.post("/cache/invalidate", dependencies=[Depends(verify_admin)])
async def invalidate_cache(req: InvalidateCacheRequest = InvalidateCacheRequest()):
    """
    Invalidate cache.
    By default, invalidates ALL caches.
    To invalidate specific parts, pass a JSON body: {"scopes": ["search"]}
    Requires admin API key.
    """

    if not cache_service:
        raise HTTPException(status_code=500, detail="Cache service not initialized")

    results = {"search": 0, "expanded_queries": 0, "total": 0}

    if "search" in req.scopes:
        deleted = await cache_service.invalidate_cache("search:*")
        results["search"] = deleted

    if "expand" in req.scopes:
        deleted = await cache_service.invalidate_cache("expand:*")
        results["expanded_queries"] = deleted

    results["total"] = results["search"] + results["expanded_queries"]

    return {"status": "success", "deleted_keys": results}


@app.get("/cache/stats", dependencies=[Depends(verify_admin)])
async def get_cache_stats():
    """Get cache statistics. Requires admin API key."""

    if not cache_service:
        raise HTTPException(status_code=500, detail="Cache service not initialized")

    stats = await cache_service.get_cache_stats()
    return {"status": "success", "stats": stats}
