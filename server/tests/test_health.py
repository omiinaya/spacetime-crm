"""Health check endpoint tests."""
import httpx
import pytest
from .conftest import SERVER_URL


class TestHealth:
    def test_health_returns_ok(self):
        resp = httpx.get(f"{SERVER_URL}/api/health", timeout=10)
        assert resp.status_code < 500, f"Health check failed: {resp.text[:200]}"
        data = resp.json()
        assert data.get("server") == "ok"

    def test_health_has_stdb_status(self):
        resp = httpx.get(f"{SERVER_URL}/api/health", timeout=10)
        data = resp.json()
        assert "stdb" in data
        assert data.get("stdb") in ("ok", "ok")

    def test_health_has_module_status(self):
        resp = httpx.get(f"{SERVER_URL}/api/health", timeout=10)
        data = resp.json()
        assert "module" in data

    def test_readiness_returns_ok(self):
        resp = httpx.get(f"{SERVER_URL}/api/health/ready", timeout=10)
        assert resp.status_code < 500, resp.text[:200]
