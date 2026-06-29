"""Shared STDB helpers, auth middleware, and constants for SpacetimeCRM.

Extracted from main.py to enable route splitting and reduce code duplication.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from pathlib import Path
import asyncio
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jinja2 import Environment, FileSystemLoader

from config import settings
from webhooks import fire_event as _fire_webhook_event, ALL_EVENTS as WEBHOOK_EVENTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# ── Jinja2 template loader ────────────────────────────────────

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

STATUS_LABELS = {
    "draft": "Draft", "sent": "Sent", "paid": "Paid",
    "partial": "Partial", "overdue": "Overdue", "cancelled": "Cancelled",
}

STATUS_CSS = {
    "draft": "draft", "sent": "sent", "paid": "paid",
    "partial": "partial", "overdue": "overdue", "cancelled": "cancelled",
}

# ── STDB helpers ──────────────────────────────────────────────


async def _sql(query: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.stdb_sql_url,
            content=query,
            headers={"Content-Type": "application/sql"},
        )
    if resp.status_code >= 400:
        logger.error("STDB SQL error: %s | query: %.200s", resp.text, query)
        raise HTTPException(502, f"SQL query failed: {resp.text[:200]}")
    data = resp.json()
    result: list[dict[str, Any]] = []
    if isinstance(data, list):
        for table_result in data:
            rows = table_result.get("rows", [])
            schema = table_result.get("schema", {})
            cols = [
                e["name"]["some"]
                for e in schema.get("elements", [])
                if "some" in e.get("name", {})
            ]
            for row in rows:
                result.append(dict(zip(cols, row)))
    return result


async def _sql_t(query: str, tenant_id: str) -> list[dict[str, Any]]:
    """Run a SELECT query with tenant_id filter automatically appended."""
    if not tenant_id:
        return await _sql(query)
    if not tenant_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid tenant_id format")
    lowered = query.lower()
    if "where" in lowered:
        for marker in (" order by", " limit", " group by", " having"):
            idx = lowered.find(marker)
            if idx != -1:
                query = query[:idx] + f" AND tenant_id = '{tenant_id}'" + query[idx:]
                return await _sql(query)
        query += f" AND tenant_id = '{tenant_id}'"
    else:
        query = query.rstrip(";")
        lowered = query.lower()
        for marker in (" order by", " limit", " group by", " having"):
            idx = lowered.find(marker)
            if idx != -1:
                query = query[:idx] + f" WHERE tenant_id = '{tenant_id}'" + query[idx:]
                return await _sql(query)
        query += f" WHERE tenant_id = '{tenant_id}'"
    return await _sql(query)


async def _paginated(
    tenant_id: str,
    table: str,
    offset: int = 0,
    limit: int = 50,
    order_by: str = "created_at",
    order_desc: bool = True,
    where_extra: str = "",
    max_fetch: int = 1000,
) -> tuple[list[dict], int]:
    """Paginated list with tenant isolation.

    STDB SQL is limited (no ORDER BY, no OFFSET) so we fetch up to
    `max_fetch` records, sort in-memory, and apply offset/limit.

    Returns (rows_slice, total_count).
    """
    conditions = [f"tenant_id = '{tenant_id}'"] if tenant_id else []
    if where_extra:
        conditions.append(where_extra)
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    count_result = await _sql(f"SELECT count(*) AS cnt FROM {table}{where_clause}")
    total = count_result[0]["cnt"] if count_result else 0

    fetch_n = min(max_fetch, total) if max_fetch else total
    query = f"SELECT * FROM {table}{where_clause}"
    if fetch_n > 0:
        query += f" LIMIT {fetch_n}"
    rows = await _sql(query)

    rows.sort(key=lambda r: (r.get(order_by) or ""), reverse=order_desc)
    return rows[offset:offset + limit], total


async def _call(reducer: str, args: list[Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.stdb_call_url}/{reducer}",
            json=args or [],
        )
    if resp.status_code >= 400:
        logger.error("STDB call error (%s): %s", reducer, resp.text[:200])
        raise HTTPException(502, f"Reducer call failed: {resp.text[:200]}")
    try:
        return resp.json()
    except Exception:
        return {"ok": True}


def _sort(rows: list[dict], key: str, desc: bool = True) -> list[dict]:
    """Sort rows by key, handling mixed types without crashing."""
    def sort_key(r):
        val = r.get(key)
        if val is None:
            return ("", 0) if desc else ("zzzz", 999999)
        return (str(val), val)
    return sorted(rows, key=sort_key, reverse=desc)


async def _log_audit(user: dict, action: str, entity: str, entity_id: str, details: str = ""):
    """Record an audit log entry. Fire-and-forget — never raises."""
    try:
        await _call("log_audit", [
            user.get("tenant_id", ""),
            user.get("id", ""),
            user.get("name", ""),
            action,
            entity,
            entity_id,
            details,
        ])
    except Exception as e:
        logger.warning("Audit log failed: %s", e)


async def _get_webhook_subscriptions() -> list[dict[str, Any]]:
    """Fetch all webhook subscriptions from STDB."""
    try:
        return await _sql("SELECT * FROM webhook_subscriptions")
    except Exception:
        return []


async def _fire_webhook(event_type: str, payload: dict[str, Any]) -> None:
    """Fire a webhook event to all matching subscriptions. Never raises."""
    try:
        subs = await _get_webhook_subscriptions()
        if subs:
            await _fire_webhook_event(event_type, payload, subs)
    except Exception as e:
        logger.warning("Webhook fire failed (%s): %s", event_type, e)


# ── Auth / Permissions ────────────────────────────────────────


def require_role(*roles: str):
    """FastAPI dependency: validate JWT and check role membership."""
    async def _check(credentials: HTTPAuthorizationCredentials = Depends(security)):
        if credentials is None:
            raise HTTPException(401, "Not authenticated")
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token: no subject")
        rows = await _sql(f"SELECT * FROM user WHERE id = '{user_id}'")
        if not rows:
            raise HTTPException(401, "User not found")
        user = rows[0]
        user["tenant_id"] = payload.get("tenant_id", "")
        if not user.get("active", False):
            raise HTTPException(403, "User account is disabled")
        if user.get("role") not in roles:
            raise HTTPException(
                403,
                f"Access denied. Requires one of roles: {', '.join(roles)}. "
                f"Your role: {user.get('role', 'unknown')}",
            )
        return user
    return _check


def _safe_id(id_str: str) -> str:
    """Validate an ID is safe for SQL interpolation. Raises 400 if not."""
    if not id_str or not id_str.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid ID format")
    return id_str


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency that validates JWT and returns user dict."""
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token: no subject")

    rows = await _sql(f"SELECT * FROM user WHERE id = '{user_id}'")
    if not rows:
        raise HTTPException(401, "User not found")
    user = rows[0]
    user["tenant_id"] = payload.get("tenant_id", "")
    if not user.get("active", False):
        raise HTTPException(403, "User account is disabled")

    return user
