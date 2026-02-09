from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    BackgroundTasks,
    HTTPException,
    File,
    UploadFile,
    Request,
    Header,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import logging
import os
import secrets
from slowapi.errors import RateLimitExceeded

from app.services.onboarding import (
    CandidateOnboardingService,
    CandidateInput,
    init_db_pool,
)
from app.services.pipeline import process_candidate_background
from app.services.parser import extract_text_from_pdf
from app.core.cache import CacheService, init_redis_pool
from app.middleware.rate_limit import (
    limiter,
    rate_limit_exceeded_handler,
    RATE_LIMIT_SEARCH,
    RATE_LIMIT_ONBOARDING,
    RATE_LIMIT_EXTRACT,
)
from rag.retriever import search_candidates
from rag.reranker import RerankerService
from rag.onboarding_graph import app_workflow

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
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, reranker, redis_client, cache_service
    logger.info("Connecting to Database...")
    db_pool = await init_db_pool()

    logger.info("Connecting to Redis...")
    redis_client = await init_redis_pool()
    cache_service = CacheService(redis_client)

    logger.info("Loading Reranker model (CrossEncoder)...")
    reranker = RerankerService()

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
    if not secrets.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return x_api_key


class SearchRequest(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    min_experience: Optional[int] = None
    top_k: int = 5


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


@app.post("/search")
@limiter.limit(RATE_LIMIT_SEARCH)
async def search_endpoint(request: Request, req: SearchRequest):
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")

    if not reranker:
        raise HTTPException(status_code=500, detail="Reranker not initialized")

    if not cache_service:
        raise HTTPException(status_code=500, detail="Cache service not initialized")

    filters = {}
    if req.location:
        filters["location"] = req.location
    if req.min_experience:
        filters["min_experience"] = req.min_experience

    # Try to get cached results
    cached_results = await cache_service.get_cached_results(req.query, filters)
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
async def invalidate_cache():
    """Invalidate all search cache. Requires admin API key."""

    if not cache_service:
        raise HTTPException(status_code=500, detail="Cache service not initialized")

    deleted_count = await cache_service.invalidate_cache()
    return {"status": "success", "deleted_keys": deleted_count}


@app.get("/cache/stats", dependencies=[Depends(verify_admin)])
async def get_cache_stats():
    """Get cache statistics. Requires admin API key."""

    if not cache_service:
        raise HTTPException(status_code=500, detail="Cache service not initialized")

    stats = await cache_service.get_cache_stats()
    return {"status": "success", "stats": stats}
