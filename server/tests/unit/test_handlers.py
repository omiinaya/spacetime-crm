import pytest


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_validation_error(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 422


def test_method_not_allowed(client):
    resp = client.put("/api/health")
    assert resp.status_code == 405
