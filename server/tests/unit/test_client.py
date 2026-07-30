"""Unit tests for server/client.py.

Tests the get_http_client() singleton function that returns a shared
httpx.AsyncClient with connection pooling.
"""

from __future__ import annotations


import httpx


class TestGetHttpClient:
    """Tests for the shared HTTP client singleton."""

    def test_returns_async_client(self) -> None:
        from client import get_http_client
        from client import _shared_client as original

        # Reset singleton for clean test
        import client as client_module

        client_module._shared_client = None
        try:
            result = get_http_client()
            assert isinstance(result, httpx.AsyncClient)
        finally:
            client_module._shared_client = original

    def test_singleton_same_instance(self) -> None:
        """Calling get_http_client() twice returns the same instance."""
        from client import get_http_client
        from client import _shared_client as original

        import client as client_module

        client_module._shared_client = None
        try:
            first = get_http_client()
            second = get_http_client()
            assert first is second
        finally:
            client_module._shared_client = original

    def test_not_none(self) -> None:
        from client import get_http_client
        from client import _shared_client as original

        import client as client_module

        client_module._shared_client = None
        try:
            result = get_http_client()
            assert result is not None
        finally:
            client_module._shared_client = original

    def test_has_expected_timeout(self) -> None:
        """Client should have a 30-second default timeout."""
        from client import get_http_client
        from client import _shared_client as original

        import client as client_module

        client_module._shared_client = None
        try:
            result = get_http_client()
            # httpx timeout is a Timeout object with read/write/connect/pool attrs
            assert result._timeout is not None
            timeout_dict = result._timeout.as_dict()
            assert timeout_dict.get("connect") == 30.0
        finally:
            client_module._shared_client = original

    def test_has_connection_limits(self) -> None:
        """Client should have connection pooling limits configured."""
        from client import get_http_client
        from client import _shared_client as original

        import client as client_module

        client_module._shared_client = None
        try:
            result = get_http_client()
            pool = result._transport._pool
            assert pool._max_keepalive_connections == 20
            assert pool._max_connections == 100
        finally:
            client_module._shared_client = original
