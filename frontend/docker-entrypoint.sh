#!/bin/sh
set -eu
cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = { API_BASE_URL: "${VITE_API_BASE_URL:-http://localhost:8000}", TRADING_API_KEY: "${TRADING_API_KEY:-}" };
EOF
exec nginx -g 'daemon off;'
