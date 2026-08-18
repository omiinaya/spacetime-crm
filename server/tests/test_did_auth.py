"""Unit tests for hermes-id DID auth (mirrors the spacetime-kanban pattern).

Pure unit tests — no STDB, no live HTTP. They exercise the fail-open /
fail-closed contract of server/did_auth.py by monkeypatching settings and
the SDK verification hook:

- Auth unconfigured (or SDK missing) → auth disabled → tokens never required.
- Auth configured + SDK present → invalid token raises 401, valid token
  returns its payload with the verified `did`.
- The /api/auth/did response shape mirrors this contract (covered by the
  endpoint smoke test in test_did_endpoint.py when running with a venv).
"""
from fastapi import HTTPException
import pytest

import config
import did_auth


@pytest.fixture(autouse=True)
def _reset_did_auth_state():
    """Reset cached card + settings between tests."""
    did_auth._server_card.cache_clear()
    yield
    did_auth._server_card.cache_clear()
    config.settings.hermes_auth_server_url = ""
    config.settings.hermes_auth_project = "crm"


def test_fail_open_when_unconfigured():
    """No HERMES_AUTH_SERVER_URL → auth disabled, tokens never enforced."""
    config.settings.hermes_auth_server_url = ""
    config.settings.hermes_auth_project = "crm"
    assert did_auth.auth_enabled() is False
    assert did_auth.auth_project() == "crm"
    # No exception, no token check — backward-compatible path.
    assert did_auth.verify_did_token("anything") is None
    assert did_auth.verify_did_token("") is None


def test_fail_open_when_sdk_missing(monkeypatch):
    """SDK unavailable → auth disabled even when a URL is configured."""
    monkeypatch.setattr(did_auth, "_SDK_AVAILABLE", False)
    config.settings.hermes_auth_server_url = "http://192.168.1.68:9488"
    assert did_auth.auth_enabled() is False
    assert did_auth.verify_did_token("anything") is None


def test_auth_project_defaults_to_crm():
    config.settings.hermes_auth_project = ""
    assert did_auth.auth_project() == "crm"
    config.settings.hermes_auth_project = "other"
    assert did_auth.auth_project() == "other"


def test_empty_token_returns_none_when_enabled():
    """Enabled + SDK present + empty token → None (no exception)."""
    config.settings.hermes_auth_server_url = "http://192.168.1.68:9488"
    assert did_auth.auth_enabled() is True
    assert did_auth.verify_did_token("") is None


def test_invalid_token_raises_401(monkeypatch):
    """Enabled + SDK present + bad token → 401 (fail-closed for bad tokens)."""
    config.settings.hermes_auth_server_url = "http://192.168.1.68:9488"
    monkeypatch.setattr(did_auth, "_server_card", lambda: {"fake": "card"})
    monkeypatch.setattr(did_auth, "_verify_token_offline", lambda *a, **k: None)
    with pytest.raises(HTTPException) as excinfo:
        did_auth.verify_did_token("garbage.token")
    assert excinfo.value.status_code == 401


def test_valid_token_returns_payload(monkeypatch):
    """Enabled + valid token → payload with verified did is returned."""
    config.settings.hermes_auth_server_url = "http://192.168.1.68:9488"
    payload = {"did": "did:hermes:test123", "aud": "crm", "expires_at": 9999999999}
    monkeypatch.setattr(did_auth, "_server_card", lambda: {"fake": "card"})
    monkeypatch.setattr(
        did_auth,
        "_verify_token_offline",
        lambda token, card, project: payload if project == "crm" else None,
    )
    result = did_auth.verify_did_token("valid.token")
    assert result is not None
    assert result == payload
    assert result["did"] == "did:hermes:test123"


def test_card_unavailable_raises_503(monkeypatch):
    """Card fetch failure with auth configured → 503 (server card unavailable)."""
    config.settings.hermes_auth_server_url = "http://192.168.1.68:9488"
    monkeypatch.setattr(did_auth, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(did_auth, "_server_card", lambda: None)  # card fetch returned nothing
    with pytest.raises(HTTPException) as excinfo:
        did_auth.verify_did_token("x.y")
    assert excinfo.value.status_code == 503