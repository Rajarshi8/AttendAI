"""
Tests for POST /api/recognize
"""
from __future__ import annotations

from unittest.mock import patch

from tests.conftest import BLANK_FRAME


BASE_PAYLOAD = {
    "frames": [BLANK_FRAME] * 6,
    "frame": BLANK_FRAME,
    "require_liveness": False,
}


def _post(client, payload: dict):
    return client.post("/api/recognize", json=payload)


class TestNoFrameSubmitted:
    def test_empty_payload(self, client):
        """Neither frame nor frames provided — 400."""
        response = _post(client, {"frames": [], "frame": None, "require_liveness": False})
        assert response.status_code == 400
        assert "frame" in response.json()["detail"].lower()


class TestFaceNotDetected:
    def test_no_embedding(self, client):
        """Frame cannot be parsed into an embedding — 400."""
        with patch("routes.recognize.face_service") as mock_face:
            mock_face.extract_embeddings.return_value = []
            mock_face.average_embedding.return_value = None
            mock_face.extract_embedding_from_frame.return_value = None

            response = _post(client, BASE_PAYLOAD)

        assert response.status_code == 400
        assert "face not detected" in response.json()["detail"].lower()


class TestSuccessfulRecognition:
    def test_matched_user(self, client, mock_cache):
        """Valid face, user in cache — returns matched=True."""
        cached_user = mock_cache.get_all()[0]

        with patch("routes.recognize.face_service") as mock_face:
            mock_face.extract_embeddings.return_value = [[0.1] * 512]
            mock_face.average_embedding.return_value = [0.1] * 512
            mock_face.extract_embedding_from_frame.return_value = [0.1] * 512
            mock_face.find_best_match.return_value = (True, cached_user, 0.93)

            response = _post(client, BASE_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["similarity"] == 0.93
        assert data["user"]["id"] == "user-test-001"


class TestNoMatchFound:
    def test_low_similarity(self, client, mock_cache):
        """Similarity below threshold — matched=False."""
        cached_user = mock_cache.get_all()[0]

        with patch("routes.recognize.face_service") as mock_face:
            mock_face.extract_embeddings.return_value = [[0.1] * 512]
            mock_face.average_embedding.return_value = [0.1] * 512
            mock_face.extract_embedding_from_frame.return_value = [0.1] * 512
            mock_face.find_best_match.return_value = (False, None, 0.30)

            response = _post(client, BASE_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False
        assert data["user"] is None
