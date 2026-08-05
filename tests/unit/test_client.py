"""Tests for client module (shared httpx.AsyncClient singleton)."""


from client import get_http_client, _shared_client


class TestGetHttpClient:
    def teardown_method(self):
        """Reset module-level state after each test."""
        import client
        client._shared_client = None

    def test_creates_new_client_when_none(self):
        cl = get_http_client()
        assert cl is not None
        assert isinstance(cl, __import__("httpx").AsyncClient)

    def test_returns_same_instance_on_repeat_call(self):
        c1 = get_http_client()
        c2 = get_http_client()
        assert c1 is c2

    def test_reset_creates_new_client(self):
        import client as cli_mod
        c1 = get_http_client()
        cli_mod._shared_client = None
        c2 = get_http_client()
        assert c1 is not c2

    def test_shared_client_is_none_initially(self):
        assert _shared_client is None
