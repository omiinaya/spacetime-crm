# ── Frontend Builder ───────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ .
RUN npm run build

# ── Runtime ────────────────────────────────────────────────
FROM python:3.12-slim

# Install runtime deps (weasyprint needs pango/cairo/etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ .

# Copy frontend dist
COPY --from=frontend /app/web/dist /app/web/dist

# Install spacetime CLI for publishing
RUN curl -L -o /tmp/spacetime.tar.gz \
    "https://github.com/clockworklabs/SpacetimeDB/releases/download/v2.4.0/spacetime-linux-x86_64.tar.gz" && \
    tar xzf /tmp/spacetime.tar.gz -C /usr/local/bin/ && \
    rm /tmp/spacetime.tar.gz && \
    chmod +x /usr/local/bin/spacetime

# Copy entrypoint
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8723
ENTRYPOINT ["/docker-entrypoint.sh"]
