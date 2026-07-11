# Root Dockerfile for spacetime-crm
# Multi-stage build: React frontend + Python backend
# The Rust STDB module is published at runtime via spacetime CLI

# ── Stage 1: Frontend Builder ────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server
COPY server/pyproject.toml server/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
RUN python3 -m playwright install chromium --with-deps 2>&1 | tail -5
COPY server/ .

COPY --from=frontend /app/web/dist /app/web/dist

RUN curl -L -o /tmp/spacetime.tar.gz \
    "https://github.com/clockworklabs/SpacetimeDB/releases/download/v2.4.0/spacetime-x86_64-unknown-linux-gnu.tar.gz" && \
    tar xzf /tmp/spacetime.tar.gz -C /usr/local/bin/ && \
    rm /tmp/spacetime.tar.gz && \
    if [ -f /usr/local/bin/spacetimedb-cli ] && [ ! -f /usr/local/bin/spacetime ]; then \
      mv /usr/local/bin/spacetimedb-cli /usr/local/bin/spacetime; \
    fi && \
    chmod +x /usr/local/bin/spacetime

COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8723/api/health/ready || exit 1

EXPOSE 8723
ENTRYPOINT ["/docker-entrypoint.sh"]
