"""hermes-id DID verification for spacetime-crm (offline-first).

Mirror of the proven spacetime-kanban did_auth.py pattern. Wraps the
hermes-id SDK so API clients can be cryptographically bound to a verified
agent DID. Verification is offline: the auth server's identity card is
fetched once and disk-cached, then every token is verified locally
(Ed25519 signature + audience + expiry). The auth server being down never
takes the CRM down — locally-valid tokens are accepted (fail-open).

Config contract (pydantic settings — see config.py / .env.example; env
vars are honored automatically by pydantic-settings):
    HERMES_AUTH_SERVER_URL   e.g. http://192.168.1.68:9488
    HERMES_AUTH_PROJECT      audience, e.g. "crm" (defaults to "crm")
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from config import settings

try:
    from hermes_id.sdk import load_server_card as _load_server_card
    from hermes_id.sdk import verify_token_offline as _verify_token_offline
    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - package optional at runtime
    _load_server_card = None
    _verify_token_offline = None
    _SDK_AVAILABLE = False


def auth_enabled() -> bool:
    """True when a hermes-id auth server URL is configured."""
    return bool(settings.hermes_auth_server_url) and _SDK_AVAILABLE


def auth_project() -> str:
    return settings.hermes_auth_project or "crm"


@lru_cache(maxsize=1)
def _server_card():
    """Fetch + cache the auth server's identity card (refreshed every 1h by SDK)."""
    url = settings.hermes_auth_server_url
    if not url:
        return None
    assert _load_server_card is not None
    return _load_server_card(url)


def verify_did_token(token: str) -> dict | None:
    """Verify a hermes-id token offline.

    Returns the token payload (with verified `did`) or None if invalid.
    Raises 401 HTTPException on an invalid token and 503 if the auth
    server's identity card cannot be loaded. When no auth server is
    configured the token is not required (backward compat / fail-open).
    """
    if not token:
        return None
    if not auth_enabled():
        return None  # no auth server configured → token not required (backward compat)

    card = _server_card()
    if card is None:
        raise HTTPException(status_code=503, detail="Hermes auth server card unavailable")

    assert _verify_token_offline is not None  # auth_enabled() already guaranteed SDK
    payload = _verify_token_offline(token, card, project=auth_project())
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or unauthorized hermes-id token")
    return payload