"""Minimal test to verify conftest works."""

from __future__ import annotations
import pytest
from starlette.testclient import TestClient


def test_app_works(client):
    r = client.get("/api/health")
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    assert data["server"] == "ok"
