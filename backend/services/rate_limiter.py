from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import get_settings

settings = get_settings()


def _parse_forwarded_for(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def get_client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = _parse_forwarded_for(xff)
            if not parts:
                return get_remote_address(request)

            if settings.trusted_proxy_count > 0 and len(parts) > settings.trusted_proxy_count:
                return parts[-(settings.trusted_proxy_count + 1)]

            return parts[0]

    return get_remote_address(request)

# Single shared limiter — attached to the FastAPI app in main.py
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[],  # Per-route limits defined on each endpoint
    headers_enabled=True,  # Adds X-RateLimit-* headers in responses
)
