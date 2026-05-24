#!/bin/sh
set -eu
cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = { API_BASE_URL: "http://81.27.108.159:8000", TRADING_API_KEY: "testkey123" };
EOF
exec nginx -g 'daemon off;'
