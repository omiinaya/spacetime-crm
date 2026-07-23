"""Unit tests for server/main.py.

Covers app structure and route registration.
The health endpoint test requires mocking the STDB HTTP client.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import main


class TestAppStructure:
    """The FastAPI app instance with expected configuration."""

    def test_app_title(self) -> None:
        assert main.app.title == "SpacetimeCRM"

    def test_app_has_spa_fallback(self) -> None:
        """The catch-all SPA route is registered."""
        paths = []
        for route in main.app.routes:
            p = getattr(route, "path", None) or (
                getattr(route, "paths", [None])[0] if hasattr(route, "paths") else None
            )
            if p:
                paths.append(p)
        assert any("full_path" in p for p in paths)


class TestHealthEndpoint:
    """The health check endpoint with mocked STDB."""

    async def _mock_stdb_ok(self, url, **kw):
        """Return a mock response that looks like STDB is working."""
        mock = AsyncMock()
        mock.status_code = 200
        return mock

    async def _mock_stdb_fail(self, url, **kw):
        """Return a mock response that looks like STDB is unreachable."""
        raise ConnectionError("STDB not running")

    def test_health_check_returns_ok_when_stdb_up(self) -> None:
        """When STDB is reachable, health returns 200."""
        mock_client = AsyncMock()
        mock_client.post.return_value = AsyncMock(status_code=200)

        with patch("routes.health.get_http_client", return_value=mock_client):
            client = TestClient(main.app)
            resp = client.get("/api/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("server") == "ok"
            assert data.get("stdb") == "ok"

    def test_health_check_returns_json(self) -> None:
        """Health response is valid JSON with expected keys regardless of STDB state."""
        client = TestClient(main.app)
        resp = client.get("/api/health")
        data = resp.json()
        assert set(data.keys()) >= {"server", "stdb", "module"}

    def test_health_ready_returns_unavailable_when_stdb_down(self) -> None:
        """Readiness probe returns unavailable when STDB is not reachable."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = ConnectionError("STDB not running")

        with patch("routes.health.get_http_client", return_value=mock_client):
            client = TestClient(main.app)
            resp = client.get("/api/health/ready")
            assert resp.status_code == 200
            assert resp.json() == {"status": "unavailable"}
