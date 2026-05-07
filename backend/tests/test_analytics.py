"""
Tests for admin analytics endpoint.
"""
from __future__ import annotations


def test_admin_can_fetch_analytics(client, mock_appwrite, admin_headers):
    mock_appwrite.get_attendance_analytics.return_value = {
        "total_students": 10,
        "present_count": 7,
        "denied_count": 3,
        "total_submissions": 10,
        "attendance_rate": 70.0,
        "average_distance": 4.2,
        "by_session": [],
    }

    response = client.get("/api/attendance/analytics", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["attendance_rate"] == 70.0


def test_student_forbidden_from_analytics(client, auth_headers):
    response = client.get("/api/attendance/analytics", headers=auth_headers)
    assert response.status_code == 403
