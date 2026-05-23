# UpCloud Deployment Guide

Deploy this project on one UpCloud Ubuntu server with Docker Compose, Nginx, Let's Encrypt SSL, PostgreSQL, and Redis running on the same server.

This guide keeps live trading disabled by default:

```env
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
API_DOCS_ENABLED=false
```

## 0. Set deployment variables

Replace these values on your local terminal notes and on the server where needed:

```bash
export BOT_DOMAIN="bot.example.com"
export API_DOMAIN="api.example.com"
export REPO_URL="https://github.com/YOUR_ORG/YOUR_REPO.git"
export DEPLOY_BRANCH="main"
export DEPLOY_USER="deploy"
export APP_DIR="/opt/ai-futures-bot"
export ADMIN_EMAIL="admin@example.com"
```

If deploying this feature branch before merge:

```bash
export DEPLOY_BRANCH="cursor/ai-futures-bot-scaffold-2acd"
```

Create DNS records before the SSL step:

```text
A  bot.example.com  -> UPCLOUD_SERVER_IPV4
A  api.example.com  -> UPCLOUD_SERVER_IPV4
```

## 1. Create the UpCloud server

In the UpCloud dashboard:

1. Create a new Cloud Server.
2. Select Ubuntu 24.04 LTS.
3. Use at least 2 vCPU, 4 GB RAM, and 50 GB storage for paper trading.
4. Add your SSH public key.
5. Deploy the server and copy its public IPv4 address.

SSH as root:

```bash
ssh root@YOUR_UPCLOUD_SERVER_IP
```

## 2. Harden Ubuntu

Run as root:

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg git ufw fail2ban unattended-upgrades nano htop openssl
```

Create a deploy user:

```bash
export DEPLOY_USER="deploy"
adduser --disabled-password --gecos "" "$DEPLOY_USER"
usermod -aG sudo "$DEPLOY_USER"
mkdir -p "/home/$DEPLOY_USER/.ssh"
cp ~/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
chmod 700 "/home/$DEPLOY_USER/.ssh"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
```

Configure firewall:

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose
```

Enable Fail2ban:

```bash
systemctl enable --now fail2ban
systemctl status fail2ban --no-pager
```

Optional after confirming key login works:

```bash
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl reload ssh
```

Log in as deploy user:

```bash
exit
ssh deploy@YOUR_UPCLOUD_SERVER_IP
```

## 3. Install Docker Compose

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
exit
ssh deploy@YOUR_UPCLOUD_SERVER_IP
```

Verify:

```bash
docker --version
docker compose version
sudo systemctl enable --now docker
```

## 4. Install Nginx and Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable --now nginx
sudo nginx -t
sudo ufw allow 'Nginx Full'
sudo ufw status verbose
```

## 5. Clone the project

```bash
export APP_DIR="/opt/ai-futures-bot"
export REPO_URL="https://github.com/YOUR_ORG/YOUR_REPO.git"
export DEPLOY_BRANCH="main"

sudo mkdir -p "$APP_DIR"
sudo chown -R "$USER:$USER" "$APP_DIR"
git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"
git checkout "$DEPLOY_BRANCH"
```

Verify files:

```bash
test -f docker-compose.yml
test -f .env.example
test -f backend/Dockerfile
test -f frontend/Dockerfile
git status --short --branch
```

## 6. Create `.env` for same-server PostgreSQL and Redis

Set domains and generate secrets:

```bash
export BOT_DOMAIN="bot.example.com"
export API_DOMAIN="api.example.com"
export TRADING_API_KEY_VALUE="$(openssl rand -hex 32)"
export POSTGRES_PASSWORD_VALUE="$(openssl rand -hex 32)"
export REDIS_PASSWORD_VALUE="$(openssl rand -hex 32)"
```

Create `.env`:

```bash
cp .env.example .env
chmod 600 .env
```

Replace placeholders and force safe paper-trading settings:

```bash
python3 - <<'PY'
from pathlib import Path
import os

path = Path('.env')
text = path.read_text()
replacements = {
    'CHANGE_ME_LONG_RANDOM_API_KEY': os.environ['TRADING_API_KEY_VALUE'],
    'CHANGE_ME_DASHBOARD_DOMAIN': os.environ['BOT_DOMAIN'],
    'CHANGE_ME_API_DOMAIN': os.environ['API_DOMAIN'],
    'CHANGE_ME_LONG_RANDOM_POSTGRES_PASSWORD': os.environ['POSTGRES_PASSWORD_VALUE'],
    'CHANGE_ME_LONG_RANDOM_REDIS_PASSWORD': os.environ['REDIS_PASSWORD_VALUE'],
}
for old, new in replacements.items():
    text = text.replace(old, new)
path.write_text(text)
PY
```

Normalize local Docker service URLs and safety flags:

```bash
python3 - <<'PY'
from pathlib import Path
import os

path = Path('.env')
lines = path.read_text().splitlines()
values = {}
for line in lines:
    if line and not line.startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        values[key] = value

pg_user = values.get('POSTGRES_USER', 'bot')
pg_db = values.get('POSTGRES_DB', 'futures_bot')
pg_password = values['POSTGRES_PASSWORD']
redis_password = values['REDIS_PASSWORD']
updates = {
    'APP_ENV': 'production',
    'API_DOCS_ENABLED': 'false',
    'CORS_ALLOWED_ORIGINS': f'https://{os.environ["BOT_DOMAIN"]}',
    'FRONTEND_API_BASE_URL': f'https://{os.environ["API_DOMAIN"]}',
    'DATABASE_URL': f'postgresql+asyncpg://{pg_user}:{pg_password}@postgres:5432/{pg_db}',
    'REDIS_URL': f'redis://:{redis_password}@redis:6379/0',
    'LIVE_TRADING_ENABLED': 'false',
    'PAPER_TRADING_ENABLED': 'true',
    'EXCHANGE_SANDBOX': 'true',
    'WORKER_STRATEGY_SCANNING_ENABLED': 'false',
}

out = []
for line in lines:
    if line and not line.startswith('#') and '=' in line:
        key = line.split('=', 1)[0]
        if key in updates:
            out.append(f'{key}={updates[key]}')
            continue
    out.append(line)
path.write_text('
'.join(out) + '
')
PY
```

Confirm no placeholders remain:

```bash
if grep -n "CHANGE_ME" .env; then
  echo "ERROR: fix unresolved placeholders"
  exit 1
fi
```

Confirm safety flags:

```bash
grep -E '^(APP_ENV|API_DOCS_ENABLED|LIVE_TRADING_ENABLED|PAPER_TRADING_ENABLED|EXCHANGE_SANDBOX|WORKER_STRATEGY_SCANNING_ENABLED)=' .env
```

Expected:

```text
APP_ENV=production
API_DOCS_ENABLED=false
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
WORKER_STRATEGY_SCANNING_ENABLED=false
```

## 7. Optional service credentials

Edit `.env` if you want OpenAI, Telegram, or exchange sandbox keys:

```bash
nano .env
```

Rules:

- Keep exchange keys empty for first infrastructure validation, or use testnet/sandbox keys.
- Never enable withdrawal permissions.
- Keep `LIVE_TRADING_ENABLED=false`.
- Keep `EXCHANGE_SANDBOX=true`.

## 8. Start Docker Compose

```bash
cd "$APP_DIR"
docker compose config
docker compose up -d --build
docker compose ps
```

View logs:

```bash
docker compose logs --tail=200 api
docker compose logs --tail=200 worker
docker compose logs --tail=100 postgres
docker compose logs --tail=100 redis
```

## 9. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

Local checks:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health/live && echo
curl -fsS http://127.0.0.1:8000/api/v1/health/ready && echo
```

## 10. Configure Nginx reverse proxy

Set domains in the shell:

```bash
export BOT_DOMAIN="bot.example.com"
export API_DOMAIN="api.example.com"
```

Create Nginx config:

```bash
sudo tee /etc/nginx/sites-available/ai-futures-bot >/dev/null <<EOF
server {
    listen 80;
    server_name ${BOT_DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    listen 80;
    server_name ${API_DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
```

Enable it:

```bash
sudo ln -sf /etc/nginx/sites-available/ai-futures-bot /etc/nginx/sites-enabled/ai-futures-bot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

HTTP tests before SSL:

```bash
curl -I "http://${BOT_DOMAIN}"
curl -fsS "http://${API_DOMAIN}/api/v1/health/live" && echo
```

## 11. Add Let's Encrypt SSL

Set email and domains:

```bash
export ADMIN_EMAIL="admin@example.com"
export BOT_DOMAIN="bot.example.com"
export API_DOMAIN="api.example.com"
```

Issue certificates and force HTTPS redirect:

```bash
sudo certbot --nginx   -d "$BOT_DOMAIN"   -d "$API_DOMAIN"   --email "$ADMIN_EMAIL"   --agree-tos   --no-eff-email   --redirect
```

Test renewal:

```bash
sudo certbot renew --dry-run
```

Verify HTTPS:

```bash
curl -I "https://${BOT_DOMAIN}"
curl -fsS "https://${API_DOMAIN}/api/v1/health/live" && echo
```

Production docs must be disabled:

```bash
curl -o /dev/null -s -w "%{http_code}
" "https://${API_DOMAIN}/docs"
curl -o /dev/null -s -w "%{http_code}
" "https://${API_DOMAIN}/openapi.json"
```

Expected for both: `404`.

## 12. Validate API authentication

Load `.env` values:

```bash
cd "$APP_DIR"
set -a
. ./.env
set +a
```

Unauthenticated protected endpoint must fail:

```bash
curl -o /dev/null -s -w "%{http_code}
" "https://${API_DOMAIN}/api/v1/dashboard/summary"
```

Expected: `401`.

Authenticated request must succeed:

```bash
curl -fsS   -H "X-API-Key: ${TRADING_API_KEY}"   "https://${API_DOMAIN}/api/v1/dashboard/summary" && echo
```

## 13. Submit a paper-trading test signal

```bash
curl -fsS -X POST "https://${API_DOMAIN}/api/v1/trading/signals/process"   -H "Content-Type: application/json"   -H "X-API-Key: ${TRADING_API_KEY}"   -d '{
    "signal": {
      "strategy_name": "ema_crossover",
      "symbol": "BTC/USDT:USDT",
      "action": "open_long",
      "confidence": 0.7,
      "entry_price": 68000,
      "stop_loss": 67184,
      "take_profit": 69632,
      "leverage": 1,
      "reason": "UpCloud paper deployment test"
    },
    "market": {
      "symbol": "BTC/USDT:USDT",
      "timeframe": "5m",
      "close": 68000,
      "volume": 1000,
      "volatility_pct": 1.5
    }
  }' && echo
```

Safe expected result:

- `paper_submitted`, or
- `blocked` with a risk/AI reason.

It must not contain a live exchange order response.

Check paper trade history:

```bash
curl -fsS   -H "X-API-Key: ${TRADING_API_KEY}"   "https://${API_DOMAIN}/api/v1/dashboard/trades" && echo
```

## 14. Keep the stack running with systemd

```bash
sudo tee /etc/systemd/system/ai-futures-bot.service >/dev/null <<EOF
[Unit]
Description=AI Futures Bot Docker Compose Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-futures-bot
sudo systemctl start ai-futures-bot
sudo systemctl status ai-futures-bot --no-pager
```

## 15. Logs and monitoring commands

```bash
cd "$APP_DIR"
docker compose ps
docker compose logs -f api
docker compose logs -f worker
```

System logs:

```bash
sudo journalctl -u ai-futures-bot -f
sudo journalctl -u nginx -f
```

Resource checks:

```bash
df -h
free -h
docker system df
```

Use an external uptime monitor for:

```text
https://api.example.com/api/v1/health/live
```

## 16. PostgreSQL backups

Create backup script:

```bash
cd "$APP_DIR"
mkdir -p backups
chmod 700 backups
cat > backup-postgres.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd /opt/ai-futures-bot
set -a
. ./.env
set +a
mkdir -p backups
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "backups/futures_bot_$(date +%F_%H%M).sql"
find backups -type f -name 'futures_bot_*.sql' -mtime +14 -delete
EOF
chmod +x backup-postgres.sh
```

Run a manual backup:

```bash
./backup-postgres.sh
ls -lh backups/
```

Install daily cron backup:

```bash
(crontab -l 2>/dev/null; echo "15 2 * * * $APP_DIR/backup-postgres.sh >> $APP_DIR/backups/backup.log 2>&1") | crontab -
crontab -l
```

## 17. Safe updates

```bash
cd "$APP_DIR"
./backup-postgres.sh
git fetch origin "$DEPLOY_BRANCH"
git status --short
git pull origin "$DEPLOY_BRANCH"
docker compose build
docker compose run --rm api alembic upgrade head
docker compose up -d
docker compose ps
curl -fsS "https://${API_DOMAIN}/api/v1/health/live" && echo
curl -fsS "https://${API_DOMAIN}/api/v1/health/ready" && echo
```

## 18. Rollback

```bash
cd "$APP_DIR"
git log --oneline -10
git checkout PREVIOUS_COMMIT_SHA
docker compose build
docker compose up -d
```

If a migration changed the database, inspect the migration before restoring backups.

## 19. Enable worker strategy scanning later

Only after manual paper tests pass:

```bash
cd "$APP_DIR"
nano .env
```

Set:

```env
WORKER_STRATEGY_SCANNING_ENABLED=true
TRADING_SYMBOLS=BTC/USDT:USDT
ENABLED_STRATEGIES=ema_crossover
```

Restart worker:

```bash
docker compose up -d worker
docker compose logs -f worker
```

Reconfirm live trading is disabled:

```bash
grep -E '^(LIVE_TRADING_ENABLED|PAPER_TRADING_ENABLED|EXCHANGE_SANDBOX)=' .env
```

Required:

```text
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
```

## 20. Emergency commands

Enable kill switch:

```bash
curl -fsS -X POST "https://${API_DOMAIN}/api/v1/trading/kill-switch/enable"   -H "X-API-Key: ${TRADING_API_KEY}" && echo
```

Stop stack:

```bash
cd "$APP_DIR"
docker compose down
```

Restart stack:

```bash
cd "$APP_DIR"
docker compose up -d
```

If credentials are compromised, revoke exchange keys in the exchange UI immediately.

## 21. Final UpCloud checklist

- [ ] DNS points `BOT_DOMAIN` and `API_DOMAIN` to the UpCloud server.
- [ ] UFW allows only SSH, HTTP, and HTTPS.
- [ ] Docker and Nginx start on boot.
- [ ] `.env` has no `CHANGE_ME` values.
- [ ] `LIVE_TRADING_ENABLED=false`.
- [ ] `PAPER_TRADING_ENABLED=true`.
- [ ] `EXCHANGE_SANDBOX=true`.
- [ ] `API_DOCS_ENABLED=false`.
- [ ] API docs return `404`.
- [ ] Unauthenticated protected API calls return `401`.
- [ ] Authenticated dashboard call succeeds.
- [ ] PostgreSQL and Redis ports are not public.
- [ ] SSL works for both domains.
- [ ] Migrations completed.
- [ ] Readiness endpoint reports DB/Redis `ok`.
- [ ] Paper signal test returns `paper_submitted` or safely `blocked`.
- [ ] PostgreSQL backup script works.
- [ ] Systemd service starts the stack.
- [ ] You can enable the kill switch quickly.
