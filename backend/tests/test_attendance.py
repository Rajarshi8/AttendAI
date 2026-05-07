"""
Tests for POST /api/attendance
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import BLANK_FRAME, MOCK_ATTENDANCE, MOCK_ATTENDANCE_DENIED, MOCK_SESSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_PAYLOAD = {
    "session_id": "session-001",
    "latitude": 12.9716,   # Same as MOCK_SESSION — inside radius
    "longitude": 77.5946,
    "frames": [BLANK_FRAME] * 8,
    "frame": BLANK_FRAME,
    "require_liveness": False,  # Disable liveness so tests focus on other logic
}


def _post(client, payload: dict):
    return client.post("/api/attendance", json=payload)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidAttendance:
    def test_happy_path(self, client, mock_appwrite, mock_cache):
        """Student inside geofence, face matches — should return marked=True."""
        mock_cache.get_all.return_value.__iter__ = MagicMock()

        with (
            patch("routes.attendance.face_service") as mock_face,
        ):
            mock_face.extract_embeddings.return_value = [[0.1] * 512]
            mock_face.average_embedding.return_value = [0.1] * 512
            mock_face.extract_embedding_from_frame.return_value = [0.1] * 512
            mock_face.find_best_match.return_value = (True, mock_cache.get_all()[0], 0.92)

            response = _post(client, BASE_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["marked"] is True
        assert data["error_code"] is None


class TestOutOfRange:
    def test_far_away_location(self, client, mock_appwrite):
        """Student 10 km away — should get OUT_OF_RANGE denial."""
        mock_appwrite.create_session_attendance.return_value = (
            True,
            MOCK_ATTENDANCE_DENIED,
            "Attendance processed.",
        )
        payload = {**BASE_PAYLOAD, "latitude": 13.10, "longitude": 77.70}  # ~18 km away
        response = _post(client, payload)

        assert response.status_code == 200
        data = response.json()
        assert data["error_code"] == "OUT_OF_RANGE"
        assert data["marked"] is True  # Denial is still recorded


class TestDuplicateAttendance:
    def test_second_submission_rejected(self, client, mock_appwrite):
        """Session already has attendance for this user — duplicate."""
        mock_appwrite.create_session_attendance.return_value = (
            False,
            MOCK_ATTENDANCE,
            "Attendance already submitted for this session.",
        )
        with patch("routes.attendance.face_service") as mock_face:
            mock_face.extract_embeddings.return_value = [[0.1] * 512]
            mock_face.average_embedding.return_value = [0.1] * 512
            mock_face.extract_embedding_from_frame.return_value = [0.1] * 512
            mock_face.find_best_match.return_value = (True, MagicMock(id="user-test-001"), 0.91)

            response = _post(client, BASE_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["marked"] is False
        assert "already" in data["message"].lower()


class TestInvalidJwt:
    def test_missing_auth_header(self):
        """No auth header — middleware should return 401."""
        # Use a raw client without auth bypass
        with patch("services.appwrite_client.appwrite_service"):
            from main import app
            from fastapi.testclient import TestClient
            raw_client = TestClient(app, raise_server_exceptions=False)

        response = raw_client.post("/api/attendance", json=BASE_PAYLOAD)
        assert response.status_code == 401


class TestLowGpsAccuracy:
    def test_low_accuracy_rejected(self, client):
        """GPS accuracy > 50m should be rejected before any face logic."""
        payload = {**BASE_PAYLOAD, "gps_accuracy": 80.0}
        response = _post(client, payload)

        assert response.status_code == 200
        data = response.json()
        assert data["error_code"] == "LOW_GPS_ACCURACY"
        assert data["marked"] is False


class TestSessionNotActive:
    def test_inactive_session(self, client, mock_appwrite):
        """Posting to an inactive session should be rejected."""
        mock_appwrite.get_session_by_id.return_value = {**MOCK_SESSION, "is_active": False}
        response = _post(client, BASE_PAYLOAD)
        assert response.status_code == 400
        assert "not active" in response.json()["detail"].lower()


class TestSessionNotFound:
    def test_unknown_session(self, client, mock_appwrite):
        """Session ID not found — 404."""
        mock_appwrite.get_session_by_id.return_value = None
        response = _post(client, BASE_PAYLOAD)
        assert response.status_code == 404
