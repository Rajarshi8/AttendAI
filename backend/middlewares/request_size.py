from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import get_settings

settings = get_settings()


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method.upper() in {"POST", "PUT", "PATCH"}:
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit():
                if int(content_length) > settings.max_request_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request payload too large."},
                    )

            body = await request.body()
            if len(body) > settings.max_request_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request payload too large."},
                )

            # Preserve body for downstream handlers
            request._body = body  # type: ignore[attr-defined]

        return await call_next(request)
