"""
Tests for POST /api/recognize
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import BLANK_FRAME


BASE_PAYLOAD = {
    "frames": [BLANK_FRAME] * 6,
    "frame": BLANK_FRAME,
    "require_liveness": False,
}


def _post(client, payload: dict, headers: dict | None = None):
    return client.post("/api/recognize", json=payload, headers=headers)


class TestNoFrameSubmitted:
    def test_empty_payload(self, client, auth_headers):
        """Neither frame nor frames provided — 400."""
        response = _post(client, {"frames": [], "frame": None, "require_liveness": False}, auth_headers)
        assert response.status_code == 400
        assert "frame" in response.json()["detail"].lower()


class TestFaceNotDetected:
    def test_no_embedding(self, client, auth_headers):
        """Frame cannot be parsed into an embedding — matched=False."""
        with patch("routes.recognize.face_service") as mock_face:
            mock_face.extract_embedding_with_reason.return_value = (
                None,
                SimpleNamespace(error_code="FACE_NOT_DETECTED"),
            )
            mock_face.average_embedding.return_value = None

            response = _post(client, BASE_PAYLOAD, auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False
        assert data["error_code"] == "FACE_NOT_DETECTED"


class TestSuccessfulRecognition:
    def test_matched_user(self, client, mock_cache, auth_headers):
        """Valid face, user in cache — returns matched=True."""
        cached_user = mock_cache.get_all()[0]

        with patch("routes.recognize.face_service") as mock_face:
            mock_face.extract_embedding_with_reason.return_value = ([0.1] * 512, None)
            mock_face.average_embedding.return_value = [0.1] * 512
            mock_face.find_best_match.return_value = (True, cached_user, 0.93)

            response = _post(client, BASE_PAYLOAD, auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["similarity"] == 0.93
        assert data["user"]["id"] == "user-test-001"


class TestNoMatchFound:
    def test_low_similarity(self, client, mock_cache, auth_headers):
        """Similarity below threshold — matched=False."""
        cached_user = mock_cache.get_all()[0]

        with patch("routes.recognize.face_service") as mock_face:
            mock_face.extract_embedding_with_reason.return_value = ([0.1] * 512, None)
            mock_face.average_embedding.return_value = [0.1] * 512
            mock_face.find_best_match.return_value = (False, None, 0.30)

            response = _post(client, BASE_PAYLOAD, auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False
        assert data["user"] is None
