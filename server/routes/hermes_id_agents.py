"""hermes-id agent approval routes — proxy to the hermes-id auth server admin API.

Admin-only endpoints that let a human admin of SpacetimeCRM review and
approve/deny hermes-id agents requesting access to this project.

The auth server admin API is protected by an X-Admin-Key header. The key is
the per-app scoped key from HERMES_ID_ADMIN_KEY (loaded from
/home/hindsight/.hermes/auth/projects/spacetime-crm.env via EnvironmentFile).
Scoped keys only touch their own project, so the project is always pinned to
HERMES_AUTH_PROJECT on every proxied request.
"""

from __future__ import annotations

import logging
import os
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from helpers import require_role

logger = logging.getLogger(__name__)

router = APIRouter()

UPSTREAM_TIMEOUT = 15.0


def _env(name: str) -> str:
    """Read a required env var, raising a descriptive error if missing."""
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is not set — cannot proxy to hermes-id auth server")
    return value


def _upstream_base() -> str:
    return _env("HERMES_AUTH_SERVER_URL").rstrip("/")


def _project() -> str:
    return _env("HERMES_AUTH_PROJECT")


def _admin_headers() -> dict[str, str]:
    return {"X-Admin-Key": _env("HERMES_ID_ADMIN_KEY")}


def _verify() -> bool | str:
    """TLS verification for the upstream call (CA bundle path or True)."""
    verify = os.environ.get("HERMES_AUTH_VERIFY", "")
    return verify or True


def _upstream_detail(resp: httpx.Response) -> str:
    """Extract a readable detail string from an upstream error response."""
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("detail"):
            return str(body["detail"])
    except Exception:
        pass
    text = resp.text.strip()
    return text[:500] if text else f"Upstream error (HTTP {resp.status_code})"


async def _proxy_get_agents(status: str) -> JSONResponse | dict:
    """GET {HERMES_AUTH_SERVER_URL}/agents?project=...&status=..."""
    url = f"{_upstream_base()}/agents"
    params = {"project": _project(), "status": status}
    try:
        async with httpx.AsyncClient(verify=_verify(), timeout=UPSTREAM_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=_admin_headers())
    except httpx.HTTPError as e:
        logger.warning("hermes-id upstream unreachable (%s): %s", url, e)
        return JSONResponse(
            status_code=502,
            content={"detail": f"hermes-id auth server unreachable: {e}"},
        )
    if resp.status_code >= 400:
        logger.warning(
            "hermes-id upstream error %s for %s: %s",
            resp.status_code,
            url,
            _upstream_detail(resp),
        )
        return JSONResponse(
            status_code=resp.status_code,
            content={"detail": _upstream_detail(resp)},
        )
    return resp.json()


async def _proxy_agent_action(did: str, action: str) -> JSONResponse | dict:
    """POST {HERMES_AUTH_SERVER_URL}/agents/{did}/{approve|deny}?project=..."""
    if not did or not did.replace("_", "").replace("-", "").replace(":", "").isalnum():
        return JSONResponse(status_code=400, content={"detail": "Invalid agent DID format"})
    url = f"{_upstream_base()}/agents/{quote(did, safe='')}/{action}"
    params = {"project": _project()}
    try:
        async with httpx.AsyncClient(verify=_verify(), timeout=UPSTREAM_TIMEOUT) as client:
            resp = await client.post(url, params=params, headers=_admin_headers())
    except httpx.HTTPError as e:
        logger.warning("hermes-id upstream unreachable (%s): %s", url, e)
        return JSONResponse(
            status_code=502,
            content={"detail": f"hermes-id auth server unreachable: {e}"},
        )
    if resp.status_code >= 400:
        logger.warning(
            "hermes-id upstream error %s for %s: %s",
            resp.status_code,
            url,
            _upstream_detail(resp),
        )
        return JSONResponse(
            status_code=resp.status_code,
            content={"detail": _upstream_detail(resp)},
        )
    try:
        return resp.json()
    except Exception:
        return {"ok": True}


@router.get("/api/admin/hermes-id/agents")
async def list_hermes_id_agents(
    status: str = "pending",
    user: dict = Depends(require_role("admin")),
):
    """List hermes-id agents for this project (default: status=pending).

    Proxies GET {HERMES_AUTH_SERVER_URL}/agents?project=...&status=...
    Returns the auth server body: {agents, total, page, page_size, pages}.
    """
    return await _proxy_get_agents(status)


@router.post("/api/admin/hermes-id/agents/{did}/approve")
async def approve_hermes_id_agent(
    did: str,
    user: dict = Depends(require_role("admin")),
):
    """Approve a hermes-id agent for this project (admin only)."""
    return await _proxy_agent_action(did, "approve")


@router.post("/api/admin/hermes-id/agents/{did}/deny")
async def deny_hermes_id_agent(
    did: str,
    user: dict = Depends(require_role("admin")),
):
    """Deny a hermes-id agent for this project (admin only)."""
    return await _proxy_agent_action(did, "deny")
