from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import get_settings

settings = get_settings()

# Single shared limiter — attached to the FastAPI app in main.py
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # Per-route limits defined on each endpoint
    headers_enabled=True,  # Adds X-RateLimit-* headers in responses
)
