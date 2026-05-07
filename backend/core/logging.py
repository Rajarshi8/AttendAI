from __future__ import annotations

import logging
import sys
from typing import Any

from core.config import get_settings

settings = get_settings()


class _StructuredFormatter(logging.Formatter):
    """Emit log records as a single-line key=value string for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras: list[str] = []
        for key in ("user_id", "session_id", "similarity", "distance", "error_code"):
            val = record.__dict__.get(key)
            if val is not None:
                extras.append(f"{key}={val}")
        if extras:
            return f"{base} | {' '.join(extras)}"
        return base


def setup_logging() -> None:
    """Configure root logger. Call once on application startup."""
    level = logging.DEBUG if settings.app_debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _StructuredFormatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Suppress noisy third-party loggers in production
    if not settings.app_debug:
        for noisy in ("deepface", "tensorflow", "keras", "urllib3", "httpx"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_recognition(
    logger: logging.Logger,
    *,
    user_id: str,
    session_id: str | None = None,
    similarity: float | None = None,
    distance: float | None = None,
    matched: bool,
    status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured recognition log line."""
    msg = f"recognition matched={matched} status={status}"
    logger.info(
        msg,
        extra={
            "user_id": user_id,
            "session_id": session_id or "",
            "similarity": f"{similarity:.4f}" if similarity is not None else "N/A",
            "distance": f"{distance:.2f}" if distance is not None else "N/A",
        },
    )
