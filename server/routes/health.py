"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from client import get_http_client
from config import settings


router = APIRouter()


@router.get("/api/health")
async def health_check():
    """Health check endpoint — verifies server and STDB connectivity."""
    results: dict = {"server": "ok", "stdb": "unknown", "module": "unknown"}
    http_code = 200

    try:
        client = get_http_client()
        resp = await client.post(
            settings.stdb_sql_url,
            content="SELECT 1 AS ok",
            headers={"Content-Type": "application/sql"},
            timeout=5,
        )
        if resp.status_code < 500:
            results["stdb"] = "ok"
            tr = await client.post(
                settings.stdb_sql_url,
                content="SELECT COUNT(*) AS c FROM customer",
                headers={"Content-Type": "application/sql"},
                timeout=5,
            )
            if tr.status_code < 500:
                results["module"] = "ok"
            else:
                tr2 = await client.post(
                    settings.stdb_sql_url,
                    content="SELECT 1 AS ok FROM user LIMIT 1",
                    headers={"Content-Type": "application/sql"},
                    timeout=5,
                )
                results["module"] = "ok" if tr2.status_code < 500 else "not published"
        else:
            results["stdb"] = f"error: {resp.status_code}"
            http_code = 503
    except Exception as e:
        results["stdb"] = f"unreachable: {e}"
        http_code = 503

    return JSONResponse(content=results, status_code=http_code)


@router.get("/api/health/ready")
async def health_ready():
    """Readiness probe — STDB must be connected."""
    try:
        client = get_http_client()
        resp = await client.post(
            settings.stdb_sql_url,
            content="SELECT 1",
            headers={"Content-Type": "application/sql"},
            timeout=3,
        )
        if resp.status_code < 500:
            return {"status": "ok"}
    except Exception:
        logger.warning("except Exception:")
        pass
    return {"status": "unavailable"}
