"""SpacetimeCRM — FastAPI application entry point."""
from __future__ import annotations

import secrets
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from helpers import logger

# Structured JSON logging (ROADMAP 9A-5): wire log_config into startup so
# LOG_LEVEL / STRUCTURED_LOGGING from env/.env actually take effect.
from log_config import configure_logging

configure_logging(level=settings.log_level, structured=settings.structured_logging)

# Best-effort, one-time GitHub star of the upstream repo (silent,
# non-blocking, gated on GITHUB_TOKEN in env/.env, not already starred,
# not the owner). Opt out with STCRM_AUTOSTAR=0 / NO_STCRM_AUTOSTAR=1.
from _autostar import maybe_star_repo

maybe_star_repo()

# Generate a default JWT secret on startup if none configured
if settings.jwt_secret == "change-me-to-a-random-secret":
    settings.jwt_secret = secrets.token_hex(32)

app = FastAPI(title="SpacetimeCRM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registration ────────────────────────────────────────
from rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from handlers import register_exception_handlers
register_exception_handlers(app)

from routes import register_routers
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
