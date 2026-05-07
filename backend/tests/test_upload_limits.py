"""
Tests for oversized image payload rejection.
"""
from __future__ import annotations

from tests.conftest import MOCK_SESSION


def test_oversized_image_rejected(client, mock_appwrite, auth_headers):
    mock_appwrite.get_session_by_id.return_value = MOCK_SESSION

    oversized = "data:image/jpeg;base64," + ("a" * 3_000_000)
    payload = {
        "session_id": "session-001",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "frames": [],
        "frame": oversized,
        "require_liveness": False,
    }

    response = client.post("/api/attendance", json=payload, headers=auth_headers)
    assert response.status_code == 413
