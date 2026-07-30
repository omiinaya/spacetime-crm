"""Unit tests for scheduler._http() singleton client."""

from __future__ import annotations

import httpx


class TestHttpClient:
    """_http() singleton client."""

    def test_returns_async_client(self) -> None:
        """Should return an httpx.AsyncClient instance."""
        from scheduler import _http

        client = _http()
        assert isinstance(client, httpx.AsyncClient)

    def test_returns_singleton(self) -> None:
        """Subsequent calls should return the same client."""
        from scheduler import _http

        client1 = _http()
        client2 = _http()
        assert client1 is client2

    def test_uses_correct_base_url(self) -> None:
        """Should be configured with localhost:8723."""
        from scheduler import _http

        client = _http()
        assert client._base_url.host == "localhost"
        assert client._base_url.port == 8723

    def test_sets_timeout(self) -> None:
        """Should have a 30s timeout with 5s connect timeout."""
        from scheduler import _http

        client = _http()
        assert client._timeout.connect == 5.0

    def test_reset_creates_new_client(self) -> None:
        """Resetting _client should create a new instance on next call."""
        import scheduler

        client1 = scheduler._http()
        scheduler._client = None
        client2 = scheduler._http()
        assert client1 is not client2
