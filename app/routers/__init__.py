from .cache import cache_router
from .candidates import candidates_router
from .cvs import cvs_router
from .queries import queries_router

__all__ = [
    "cache_router",
    "candidates_router",
    "cvs_router",
    "queries_router",
]
