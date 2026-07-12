"""SpacetimeCRM — FastAPI application entry point."""

from __future__ import annotations

import secrets
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from log_config import configure_logging

# Generate a default signing key on startup if none configured
if settings.jwt_secret == "set-via-environment-variable":  # pragma: allowlist secret
    settings.jwt_secret = secrets.token_hex(32)

# Initialize structured logging
configure_logging()

app = FastAPI(title="SpacetimeCRM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        settings.cors_origin.replace("https://", "").replace("http://", "").split(":")[0],
        "localhost",
        "127.0.0.1",
        "*.onrender.com",
        "*.fly.dev",
    ],
)

# ── Route registration ────────────────────────────────────────
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from rate_limit import limiter

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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.server_port,
        reload=True,
        log_config=None,  # Use our own logging config from log_config.py
    )
