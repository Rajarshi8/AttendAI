from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import get_logger
from services.rate_limiter import get_client_ip

logger = get_logger("request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        request.state.client_ip = get_client_ip(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "user_id": getattr(request.state, "user_id", ""),
                "session_id": getattr(request.state, "session_id", ""),
                "error_code": getattr(request.state, "error_code", None),
                "client_ip": request.state.client_ip,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": f"{duration_ms:.2f}",
            },
        )

        return response
