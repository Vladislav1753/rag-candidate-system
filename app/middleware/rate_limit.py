"""
Rate limiting middleware using slowapi.
Protects endpoints from abuse by limiting the number of requests per time window.
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Rate limit configuration from environment variables
RATE_LIMIT_SEARCH = os.getenv("RATE_LIMIT_SEARCH", "20/hour")
RATE_LIMIT_ONBOARDING = os.getenv("RATE_LIMIT_ONBOARDING", "20/hour")
RATE_LIMIT_EXTRACT = os.getenv("RATE_LIMIT_EXTRACT", "20/hour")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "20/hour")

# Redis configuration (optional, falls back to in-memory storage)
REDIS_URL = os.getenv(
    "REDIS_URL"
)  # e.g., "redis://localhost:6379" or "redis://redis:6379"


def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses IP address or API key from header if available.
    """
    # Try to get API key from header first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"

    # Fall back to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return get_remote_address(request)


# Initialize limiter
# Uses Redis if REDIS_URL is set, otherwise falls back to in-memory storage
storage_uri = REDIS_URL if REDIS_URL else "memory://"
logger.info(f"Rate limiter using storage: {storage_uri.split('://')[0]}://...")

limiter = Limiter(
    key_func=get_identifier,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri=storage_uri,
    strategy="fixed-window",
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    Returns JSON response with retry information.
    """
    logger.warning(
        f"Rate limit exceeded for {get_identifier(request)} on {request.url.path}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.detail,
        },
        headers={"Retry-After": str(exc.detail)},
    )
