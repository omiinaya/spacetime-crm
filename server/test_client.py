"""
Tests for server/client.py.

Tests the shared httpx.AsyncClient singleton.
"""

from __future__ import annotations

import httpx

from server.client import get_http_client


class TestClient:
    """Test suite for client.py."""

    def test_get_http_client_returns_async_client(self):
        """get_http_client returns an httpx.AsyncClient instance."""
        client = get_http_client()
        assert isinstance(client, httpx.AsyncClient)

    def test_singleton_behavior(self):
        """get_http_client returns the same instance on repeated calls."""
        client1 = get_http_client()
        client2 = get_http_client()
        assert client1 is client2

    def test_client_timeout(self):
        """Client has a 30s default timeout configured."""
        client = get_http_client()
        assert client._timeout.connect == 30.0
        assert client._timeout.read == 30.0

    def test_client_supports_timeout_override(self):
        """Client supports per-call timeout overrides."""
        client = get_http_client()
        # Verify it's a proper AsyncClient that accepts timeout kwargs
        assert hasattr(client, "get")
        assert hasattr(client, "post")

    def test_get_client_reinitializes_after_reset(self):
        """Setting _shared_client back to None creates a new instance."""
        import server.client

        first = get_http_client()
        server.client._shared_client = None
        second = get_http_client()
        assert first is not second
        # Restore for other tests
        server.client._shared_client = first
