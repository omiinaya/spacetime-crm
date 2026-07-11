# ── Frontend Builder ───────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ── Runtime ────────────────────────────────────────────────
FROM python:3.12-slim

# Minimal system deps — Playwright install --with-deps handles Chromium deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install Chromium for PDF generation (replaces weasyprint — smaller, modern CSS)
RUN python3 -m playwright install chromium --with-deps 2>&1 | tail -5
COPY server/ .

# Copy frontend dist
COPY --from=frontend /app/web/dist /app/web/dist

# Install spacetime CLI for publishing
RUN curl -L -o /tmp/spacetime.tar.gz \
    "https://github.com/clockworklabs/SpacetimeDB/releases/download/v2.4.0/spacetime-x86_64-unknown-linux-gnu.tar.gz" && \
    tar xzf /tmp/spacetime.tar.gz -C /usr/local/bin/ && \
    rm /tmp/spacetime.tar.gz && \
    if [ -f /usr/local/bin/spacetimedb-cli ] && [ ! -f /usr/local/bin/spacetime ]; then \
      mv /usr/local/bin/spacetimedb-cli /usr/local/bin/spacetime; \
    fi && \
    chmod +x /usr/local/bin/spacetime

# Copy entrypoint
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Health check — used by orchestrators and docker-compose
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8723/api/health/ready || exit 1

EXPOSE 8723
ENTRYPOINT ["/docker-entrypoint.sh"]
