import pytest


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_wrong_method(client):
    resp = client.put("/api/health")
    assert resp.status_code == 405
    resp = client.post("/api/health")
    assert resp.status_code == 405
    resp = client.delete("/api/health")
    assert resp.status_code == 405
