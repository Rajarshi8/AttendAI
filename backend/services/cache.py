from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import TYPE_CHECKING

from core.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingCache:
    """
    In-memory store of user_id → embedding, loaded from Appwrite.

    Thread-safe for concurrent FastAPI requests.
    Auto-refreshes on access if data is older than `refresh_interval_minutes`.
    """

    def __init__(self, refresh_interval_minutes: int | None = None) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, list[float]] = {}
        self._meta: dict[str, dict] = {}  # user_id → {name, email}
        self._last_refresh: datetime | None = None
        self._refresh_interval_minutes = (
            refresh_interval_minutes
            if refresh_interval_minutes is not None
            else settings.cache_refresh_interval_minutes
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Force-load all embeddings from Appwrite. Called on startup."""
        self._refresh()

    def refresh_if_stale(self) -> None:
        """Refresh the cache if it has never been loaded or TTL has expired."""
        if self._is_stale():
            self._refresh()

    def invalidate(self) -> None:
        """Mark cache as stale so the next request will reload it."""
        with self._lock:
            self._last_refresh = None
        logger.info("EmbeddingCache: invalidated — will reload on next request.")

    def get_all(self) -> list[SimpleNamespace]:
        """
        Return a list of user namespace objects compatible with
        `face_service.find_best_match()`.

        Each object has: .id, .user_code, .name, .email, .embedding
        """
        self.refresh_if_stale()
        with self._lock:
            return [
                SimpleNamespace(
                    id=uid,
                    user_code=uid,
                    name=self._meta.get(uid, {}).get("name", "Unknown"),
                    email=self._meta.get(uid, {}).get("email", ""),
                    embedding=emb,
                )
                for uid, emb in self._store.items()
                if emb  # skip users with no embedding
            ]

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_stale(self) -> bool:
        with self._lock:
            if self._last_refresh is None:
                return True
            elapsed = (datetime.now(timezone.utc) - self._last_refresh).total_seconds()
            return elapsed > (self._refresh_interval_minutes * 60)

    def _refresh(self) -> None:
        # Import here to avoid circular imports at module level
        from services.appwrite_client import appwrite_service  # noqa: PLC0415

        logger.info("EmbeddingCache: refreshing from Appwrite…")
        try:
            docs = appwrite_service.get_all_users()
            new_store: dict[str, list[float]] = {}
            new_meta: dict[str, dict] = {}
            for doc in docs:
                uid = str(doc.get("user_id") or doc.get("$id") or "")
                if not uid:
                    continue
                embedding = doc.get("embedding") or []
                new_store[uid] = embedding
                new_meta[uid] = {
                    "name": doc.get("name") or "Unknown",
                    "email": doc.get("email") or "",
                }

            with self._lock:
                self._store = new_store
                self._meta = new_meta
                self._last_refresh = datetime.now(timezone.utc)

            logger.info(
                "EmbeddingCache: loaded %d users (%d with embeddings).",
                len(new_store),
                sum(1 for e in new_store.values() if e),
            )
        except Exception as exc:
            logger.error("EmbeddingCache: refresh failed — %s", exc)


# Singleton — imported by routes
embedding_cache = EmbeddingCache()
