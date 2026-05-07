from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core.config import get_settings
from core.logging import setup_logging, get_logger
from middlewares import AppwriteAuthMiddleware
from routes import attendance_router, recognize_router, register_router, sessions_router, users_router
from services.cache import embedding_cache
from services.rate_limiter import limiter

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup: pre-load embedding cache. Shutdown: no-op."""
    logger.info("AttendAI starting up — pre-loading embedding cache…")
    try:
        embedding_cache.load()
        logger.info("Embedding cache ready with %d users.", embedding_cache.size())
    except Exception as exc:
        logger.warning("Could not pre-load embedding cache: %s — will load on first request.", exc)
    yield
    logger.info("AttendAI shutting down.")


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
)

# Attach rate limiter to the app state (required by slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AppwriteAuthMiddleware)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        "cache_size": embedding_cache.size(),
    }


app.include_router(register_router, prefix=settings.api_prefix)
app.include_router(recognize_router, prefix=settings.api_prefix)
app.include_router(attendance_router, prefix=settings.api_prefix)
app.include_router(sessions_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
