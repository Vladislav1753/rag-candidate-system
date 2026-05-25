import asyncio
import logging
import sys
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import (
    FastAPI,
)
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.cache import CacheService, init_redis_pool
from app.middleware.rate_limit import (
    limiter,
    rate_limit_exceeded_handler,
)
from app.routers import cache_router, candidates_router, cvs_router, queries_router
from app.services.onboarding import (
    init_db_pool,
)
from rag.agents.query_expansion_agent import QueryExpansionAgent
from rag.reranker import RerankerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        logger.info("Connecting to Database...")
        app.state.db_pool = await init_db_pool()
        stack.push_async_callback(app.state.db_pool.close)

        logger.info("Connecting to Redis...")
        app.state.redis_client = await init_redis_pool()
        stack.push_async_callback(app.state.redis_client.close)

        app.state.cache_service = CacheService(app.state.redis_client)

        logger.info("Loading Reranker model (CrossEncoder)...")
        app.state.reranker = await asyncio.to_thread(RerankerService)

        logger.info("Initializing Query Expansion Agent...")
        app.state.query_expander = QueryExpansionAgent()

        yield


app = FastAPI(lifespan=lifespan)

app.include_router(candidates_router)
app.include_router(cache_router)

app.include_router(cvs_router)

app.include_router(queries_router)

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
