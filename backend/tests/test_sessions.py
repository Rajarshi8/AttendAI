"""
Tests for session start/stop endpoints with role enforcement.
"""
from __future__ import annotations

from tests.conftest import MOCK_SESSION


BASE_PAYLOAD = {
    "class_name": "Computer Networks",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "radius_meters": 75,
}


def test_admin_can_start_session(client, mock_appwrite, admin_headers):
    mock_appwrite.create_session.return_value = MOCK_SESSION
    response = client.post("/api/sessions/start", json=BASE_PAYLOAD, headers=admin_headers)
    assert response.status_code == 200


def test_student_cannot_start_session(client, auth_headers):
    response = client.post("/api/sessions/start", json=BASE_PAYLOAD, headers=auth_headers)
    assert response.status_code == 403


def test_admin_can_stop_own_session(client, mock_appwrite, admin_headers):
    mock_appwrite.get_session_by_id.return_value = {**MOCK_SESSION, "admin_id": "admin-001"}
    mock_appwrite.stop_session.return_value = {**MOCK_SESSION, "is_active": False}

    response = client.post("/api/sessions/stop", json={"session_id": "session-001"}, headers=admin_headers)
    assert response.status_code == 200


def test_admin_cannot_stop_other_session(client, mock_appwrite, admin_headers):
    mock_appwrite.get_session_by_id.return_value = {**MOCK_SESSION, "admin_id": "other-admin"}
    response = client.post("/api/sessions/stop", json={"session_id": "session-001"}, headers=admin_headers)
    assert response.status_code == 403
