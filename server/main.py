"""SpacetimeCRM — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

# Initialize structured logging (import triggers configure_logging)
import log_config  # noqa: F401
import uvicorn
from config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── Background scheduler ───────────────────────────────────

_scheduler_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background scheduler tasks on startup, clean up on shutdown."""
    from scheduler import SCHEDULED_TASKS

    for name, (coro, interval) in SCHEDULED_TASKS.items():
        task = asyncio.create_task(coro(interval), name=f"scheduler:{name}")
        _scheduler_tasks.append(task)
        print(f"[scheduler] Started: {name} (every {interval}s)")

    yield

    for task in _scheduler_tasks:
        task.cancel()
    await asyncio.gather(*_scheduler_tasks, return_exceptions=True)
    print("[scheduler] All tasks stopped")


# Generate a default JWT secret on startup if none configured
if settings.jwt_secret == "change-me-to-a-random-secret":
    settings.jwt_secret = secrets.token_hex(32)

app = FastAPI(
    title="SpacetimeCRM",
    description="RepairShopr-inspired CRM built on SpacetimeDB — customers, tickets, invoicing, appointments, inventory, and POS.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "SpacetimeCRM",
        "url": "https://github.com/omiinaya/spacetime-crm",
    },
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registration ────────────────────────────────────────
from rate_limit import limiter  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from handlers import register_exception_handlers  # noqa: E402

register_exception_handlers(app)

from routes import register_routers  # noqa: E402

register_routers(app)

# ── SPA static files ──────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "web" / "dist"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"detail": "Not Found"}


# ── ENTRY ─────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.server_port, reload=True)
