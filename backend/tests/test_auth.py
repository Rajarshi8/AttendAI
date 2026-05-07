"""
Tests for JWT middleware enforcement.
"""
from __future__ import annotations


def test_missing_auth_header_rejected(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_invalid_token_rejected(client):
    response = client.get("/api/users/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
