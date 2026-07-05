#!/bin/bash
# ── SpacetimeCRM Production Deploy Script ───────────────────
# Sets up nginx config, self-signed TLS certs, and enables the site.
#
# Usage:
#   sudo bash deploy/nginx/deploy.sh [domain]
#
# If a domain is provided, self-signed cert uses that domain.
# Default: spacetime-crm.local
#
# For production with real domain and Let's Encrypt:
#   sudo bash deploy/nginx/deploy.sh your-domain.com
#   sudo certbot --nginx -d your-domain.com

set -euo pipefail

DOMAIN="${1:-spacetime-crm.local}"
CONFIG_SRC="$(dirname "$0")/spacetime-crm.conf"
NGINX_AVAILABLE="/etc/nginx/sites-available/spacetime-crm"
NGINX_ENABLED="/etc/nginx/sites-enabled/spacetime-crm"

echo "🔧 Deploying SpacetimeCRM nginx config for domain: $DOMAIN"

# ── Validate nginx is installed ──────────────────────────────
if ! command -v nginx &>/dev/null; then
    echo "❌ nginx is not installed. Install with: apt-get install nginx"
    exit 1
fi

# ── Copy nginx config ────────────────────────────────────────
echo "📄 Copying nginx config..."
cp "$CONFIG_SRC" "$NGINX_AVAILABLE"

# Replace default server_name with domain
sed -i "s/server_name _;/server_name $DOMAIN;/g" "$NGINX_AVAILABLE"

# ── Create self-signed TLS certificate (if Let's Encrypt certs don't exist) ──
CERT_DIR="/etc/ssl"
CERT_FILE="$CERT_DIR/certs/spacetime-crm.crt"
KEY_FILE="$CERT_DIR/private/spacetime-crm.key"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "✅ TLS certificates already exist at $CERT_FILE"
else
    echo "🔑 Generating self-signed TLS certificate (valid 365 days)..."
    mkdir -p "$CERT_DIR/certs" "$CERT_DIR/private"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:192.168.1.10"
    chmod 600 "$KEY_FILE"
    echo "✅ Self-signed certificate created"
fi

# ── Enable site ──────────────────────────────────────────────
echo "🔗 Enabling site..."
ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"

# ── Test and reload ──────────────────────────────────────────
echo "🧪 Testing nginx configuration..."
nginx -t

echo "🔄 Reloading nginx..."
systemctl reload nginx || systemctl restart nginx

echo ""
echo "✅ SpacetimeCRM nginx setup complete!"
echo "   URL: https://$DOMAIN"
echo "   Config: $NGINX_AVAILABLE"
echo ""
echo "⚠️  Self-signed cert warning in browser — this is expected."
echo "   For production, run: sudo certbot --nginx -d $DOMAIN"
