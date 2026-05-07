"""
pytest conftest — shared fixtures for AttendAI backend tests.

Mocks:
    - appwrite_service  (no real Appwrite connection)
    - embedding_cache   (isolated in-memory store)
    - FastAPI TestClient using real auth middleware with mocked JWT validation
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Test tokens (validated by mocked Appwrite service)
# ---------------------------------------------------------------------------

TOKEN_STUDENT = "test-student-token"
TOKEN_ADMIN = "test-admin-token"

# ---------------------------------------------------------------------------
# Shared mock objects
# ---------------------------------------------------------------------------

MOCK_SESSION = {
    "$id": "session-001",
    "session_id": "session-001",
    "admin_id": "admin-001",
    "class_name": "Math 101",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "radius_meters": 100.0,
    "is_active": True,
    "start_time": "2026-04-13T10:00:00+00:00",
    "end_time": None,
}

MOCK_ATTENDANCE = {
    "$id": "att-001",
    "id": "att-001",
    "user_id": "user-test-001",
    "session_id": "session-001",
    "timestamp": "2026-04-13T10:05:00+00:00",
    "date": "2026-04-13",
    "status": "present",
    "distance": 5.0,
}

MOCK_ATTENDANCE_DENIED = {**MOCK_ATTENDANCE, "status": "denied", "id": "att-002", "$id": "att-002"}

MOCK_USER_DOC = {
    "$id": "user-test-001",
    "user_id": "user-test-001",
    "name": "Test User",
    "email": "test@example.com",
    "role": "student",
    "embedding": [0.1] * 512,
}


# ---------------------------------------------------------------------------
# A tiny 1x1 black JPEG as base64 (valid image for frame decode)
# ---------------------------------------------------------------------------

import base64, cv2  # noqa: E402

def _blank_frame_b64() -> str:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf.tobytes()).decode()


BLANK_FRAME = _blank_frame_b64()


# ---------------------------------------------------------------------------
# conftest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_appwrite():
    svc = MagicMock()

    def _jwt_lookup(token: str):
        if token == TOKEN_ADMIN:
            return {"$id": "admin-001", "email": "admin@example.com", "name": "Admin User"}
        if token == TOKEN_STUDENT:
            return {"$id": "user-test-001", "email": "test@example.com", "name": "Test User"}
        raise Exception("invalid token")

    svc.validate_jwt.side_effect = _jwt_lookup
    svc.get_user_role.side_effect = lambda uid: "admin" if uid == "admin-001" else "student"
    svc.get_session_by_id.return_value = MOCK_SESSION
    svc.find_attendance_for_session.return_value = None
    svc.create_session_attendance.return_value = (True, MOCK_ATTENDANCE, "Attendance processed successfully.")
    svc.get_all_users.return_value = [MOCK_USER_DOC]
    return svc


@pytest.fixture()
def mock_cache():
    cache = MagicMock()
    cache.get_all.return_value = [
        SimpleNamespace(
            id="user-test-001",
            user_code="user-test-001",
            name="Test User",
            email="test@example.com",
            embedding=[0.1] * 512,
        )
    ]
    cache.size.return_value = 1
    cache.refresh_if_stale.return_value = None
    cache.load.return_value = None
    cache.refresh_loop = AsyncMock()
    return cache


@pytest.fixture()
def client(mock_appwrite, mock_cache):
    """TestClient with mocked Appwrite + cache + auth bypass."""
    with (
        patch("services.appwrite_client.appwrite_service", mock_appwrite),
        patch("middlewares.auth.appwrite_service", mock_appwrite),
        patch("routes.attendance.appwrite_service", mock_appwrite),
        patch("routes.attendance.embedding_cache", mock_cache),
        patch("routes.recognize.embedding_cache", mock_cache),
        patch("services.cache.embedding_cache", mock_cache),
    ):
        from main import app
        yield TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def auth_headers():
    return {"Authorization": f"Bearer {TOKEN_STUDENT}"}


@pytest.fixture()
def admin_headers():
    return {"Authorization": f"Bearer {TOKEN_ADMIN}"}
