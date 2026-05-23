# UpCloud Final Launch Checklist

Follow this checklist in order when deploying to UpCloud today. This launch is **paper trading only**.

Required safety defaults for today:

```env
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
API_DOCS_ENABLED=false
WORKER_STRATEGY_SCANNING_ENABLED=false
```

## 1. Prepare launch values

Set these values in your notes first:

```bash
export UPCLOUD_IP="YOUR_UPCLOUD_SERVER_IP"
export BOT_DOMAIN="bot.example.com"
export API_DOMAIN="api.example.com"
export REPO_URL="https://github.com/YOUR_ORG/YOUR_REPO.git"
export DEPLOY_BRANCH="main"
export DEPLOY_USER="deploy"
export APP_DIR="/opt/ai-futures-bot"
export ADMIN_EMAIL="admin@example.com"
```

If launching this branch before merge:

```bash
export DEPLOY_BRANCH="cursor/ai-futures-bot-scaffold-2acd"
```

## 2. Create the UpCloud server

- [ ] Create Ubuntu 24.04 LTS server.
- [ ] Use at least 2 vCPU, 4 GB RAM, 50 GB disk.
- [ ] Add your SSH public key.
- [ ] Copy the public IPv4 to `UPCLOUD_IP`.

## 3. Point DNS to the server

Create DNS records:

```text
A  BOT_DOMAIN  -> UPCLOUD_IP
A  API_DOMAIN  -> UPCLOUD_IP
```

Verify:

```bash
dig +short "$BOT_DOMAIN"
dig +short "$API_DOMAIN"
```

Expected:

- [ ] Both return the UpCloud IP.

## 4. SSH into UpCloud as root

```bash
ssh root@"$UPCLOUD_IP"
```

Set variables on the server:

```bash
export BOT_DOMAIN="bot.example.com"
export API_DOMAIN="api.example.com"
export REPO_URL="https://github.com/YOUR_ORG/YOUR_REPO.git"
export DEPLOY_BRANCH="main"
export DEPLOY_USER="deploy"
export APP_DIR="/opt/ai-futures-bot"
export ADMIN_EMAIL="admin@example.com"
```

## 5. Update and harden Ubuntu

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg git ufw fail2ban unattended-upgrades nano htop openssl dnsutils
```

Create deploy user:

```bash
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

Expected:

- [ ] UFW active.
- [ ] Only SSH, HTTP, HTTPS open.
- [ ] Fail2ban running.

## 6. Log in as deploy user

```bash
exit
ssh "$DEPLOY_USER@$UPCLOUD_IP"
```

Set variables again:

```bash
export BOT_DOMAIN="bot.example.com"
export API_DOMAIN="api.example.com"
export REPO_URL="https://github.com/YOUR_ORG/YOUR_REPO.git"
export DEPLOY_BRANCH="main"
export APP_DIR="/opt/ai-futures-bot"
export ADMIN_EMAIL="admin@example.com"
```

## 7. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
exit
ssh "$DEPLOY_USER@$UPCLOUD_IP"
```

Verify:

```bash
docker --version
docker compose version
sudo systemctl enable --now docker
```

Expected:

- [ ] Docker works without sudo.
- [ ] Docker Compose works.

## 8. Install Nginx and Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable --now nginx
sudo nginx -t
sudo ufw allow 'Nginx Full'
sudo ufw status verbose
```

Expected:

- [ ] Nginx config test succeeds.
- [ ] Nginx running.

## 9. Clone the project

```bash
sudo mkdir -p "$APP_DIR"
sudo chown -R "$USER:$USER" "$APP_DIR"
git clone "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"
git checkout "$DEPLOY_BRANCH"
```

Verify:

```bash
test -f docker-compose.yml
test -f .env.example
test -f backend/Dockerfile
test -f frontend/Dockerfile
git status --short --branch
```

Expected:

- [ ] Required files exist.
- [ ] Correct branch checked out.
- [ ] No unexpected local changes.

## 10. Create production `.env`

Generate secrets:

```bash
export TRADING_API_KEY_VALUE="$(openssl rand -hex 32)"
export POSTGRES_PASSWORD_VALUE="$(openssl rand -hex 32)"
export REDIS_PASSWORD_VALUE="$(openssl rand -hex 32)"
```

Create `.env`:

```bash
cp .env.example .env
chmod 600 .env
```

Replace placeholders:

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

Normalize local PostgreSQL/Redis URLs and force safe paper settings:

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
path.write_text('\n'.join(out) + '\n')
PY
```

Verify no placeholders remain:

```bash
if grep -n "CHANGE_ME" .env; then
  echo "ERROR: unresolved placeholders remain"
  exit 1
fi
```

Verify safe launch flags:

```bash
grep -E '^(APP_ENV|API_DOCS_ENABLED|LIVE_TRADING_ENABLED|PAPER_TRADING_ENABLED|EXCHANGE_SANDBOX|WORKER_STRATEGY_SCANNING_ENABLED)=' .env
```

Required:

```text
APP_ENV=production
API_DOCS_ENABLED=false
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
WORKER_STRATEGY_SCANNING_ENABLED=false
```

Stop if any value differs.

## 11. Optional credentials for today

For first launch:

- [ ] Leave exchange keys empty, or use testnet/sandbox keys only.
- [ ] Never use withdrawal-enabled keys.
- [ ] Add Telegram credentials if you want alerts.
- [ ] Add OpenAI key if you want AI analysis in paper mode.

Edit only if needed:

```bash
nano .env
```

Recheck safety flags:

```bash
grep -E '^(LIVE_TRADING_ENABLED|PAPER_TRADING_ENABLED|EXCHANGE_SANDBOX|API_DOCS_ENABLED)=' .env
```

## 12. Build and start Docker Compose

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

Expected:

- [ ] `api` running.
- [ ] `worker` running.
- [ ] `frontend` running.
- [ ] `postgres` healthy or starting.
- [ ] `redis` healthy or starting.

Check logs:

```bash
docker compose logs --tail=200 api
docker compose logs --tail=200 worker
docker compose logs --tail=100 postgres
docker compose logs --tail=100 redis
```

## 13. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

Expected:

- [ ] Migration completes without errors.

## 14. Check local health before Nginx

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health/live && echo
curl -fsS http://127.0.0.1:8000/api/v1/health/ready && echo
```

Expected:

- [ ] Liveness returns `ok`.
- [ ] Readiness reports database `ok`.
- [ ] Readiness reports Redis `ok`.

## 15. Configure Nginx reverse proxy

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

Enable site:

```bash
sudo ln -sf /etc/nginx/sites-available/ai-futures-bot /etc/nginx/sites-enabled/ai-futures-bot
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

HTTP checks:

```bash
curl -I "http://${BOT_DOMAIN}"
curl -fsS "http://${API_DOMAIN}/api/v1/health/live" && echo
```

Expected:

- [ ] Dashboard domain responds over HTTP.
- [ ] API health responds over HTTP.

## 16. Issue Let’s Encrypt SSL

```bash
sudo certbot --nginx \
  -d "$BOT_DOMAIN" \
  -d "$API_DOMAIN" \
  --email "$ADMIN_EMAIL" \
  --agree-tos \
  --no-eff-email \
  --redirect
```

Test renewal:

```bash
sudo certbot renew --dry-run
```

HTTPS checks:

```bash
curl -I "https://${BOT_DOMAIN}"
curl -fsS "https://${API_DOMAIN}/api/v1/health/live" && echo
```

Expected:

- [ ] HTTPS works for both domains.
- [ ] HTTP redirects to HTTPS.
- [ ] Certbot dry run succeeds.

## 17. Confirm production docs are disabled

```bash
curl -o /dev/null -s -w "%{http_code}\n" "https://${API_DOMAIN}/docs"
curl -o /dev/null -s -w "%{http_code}\n" "https://${API_DOMAIN}/openapi.json"
```

Expected:

```text
404
404
```

Stop if either returns `200`.

## 18. Validate API authentication

Load `.env`:

```bash
set -a
. ./.env
set +a
```

Unauthenticated request:

```bash
curl -o /dev/null -s -w "%{http_code}\n" "https://${API_DOMAIN}/api/v1/dashboard/summary"
```

Expected: `401`.

Authenticated request:

```bash
curl -fsS \
  -H "X-API-Key: ${TRADING_API_KEY}" \
  "https://${API_DOMAIN}/api/v1/dashboard/summary" && echo
```

Expected:

- [ ] Dashboard JSON returned.

## 19. Submit one paper test signal

```bash
curl -fsS -X POST "https://${API_DOMAIN}/api/v1/trading/signals/process" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${TRADING_API_KEY}" \
  -d '{
    "signal": {
      "strategy_name": "ema_crossover",
      "symbol": "BTC/USDT:USDT",
      "action": "open_long",
      "confidence": 0.7,
      "entry_price": 68000,
      "stop_loss": 67184,
      "take_profit": 69632,
      "leverage": 1,
      "reason": "final UpCloud launch paper test"
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

- [ ] `paper_submitted`, or
- [ ] `blocked` with a clear safety/risk/AI reason.

Stop if you see a live exchange order response.

## 20. Confirm paper trade history

```bash
curl -fsS \
  -H "X-API-Key: ${TRADING_API_KEY}" \
  "https://${API_DOMAIN}/api/v1/dashboard/trades" && echo
```

Expected:

- [ ] Endpoint returns JSON.
- [ ] If the paper signal was submitted, the paper trade appears.

## 21. Create and test database backups

```bash
mkdir -p "$APP_DIR/backups"
chmod 700 "$APP_DIR/backups"
cat > "$APP_DIR/backup-postgres.sh" <<'EOF'
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
chmod +x "$APP_DIR/backup-postgres.sh"
"$APP_DIR/backup-postgres.sh"
ls -lh "$APP_DIR/backups"
```

Expected:

- [ ] A `.sql` backup file exists.

Add daily cron:

```bash
(crontab -l 2>/dev/null; echo "15 2 * * * $APP_DIR/backup-postgres.sh >> $APP_DIR/backups/backup.log 2>&1") | crontab -
crontab -l
```

## 22. Add systemd restart service

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
sudo systemctl daemon-reload
sudo systemctl enable ai-futures-bot
sudo systemctl start ai-futures-bot
sudo systemctl status ai-futures-bot --no-pager
```

Expected:

- [ ] Service enabled.
- [ ] Service status successful.

## 23. Open monitoring logs

```bash
cd "$APP_DIR"
docker compose logs -f api worker
```

In another terminal:

```bash
df -h
free -h
docker compose ps
docker system df
```

Expected:

- [ ] No repeated API errors.
- [ ] No repeated worker errors.
- [ ] Disk and memory healthy.

## 24. Keep worker strategy scanning disabled today

Confirm:

```bash
grep '^WORKER_STRATEGY_SCANNING_ENABLED=' .env
```

Required:

```text
WORKER_STRATEGY_SCANNING_ENABLED=false
```

Only enable worker scanning after manual tests, health checks, backups, and logs are clean.

## 25. Keep emergency kill switch ready

```bash
curl -fsS -X POST "https://${API_DOMAIN}/api/v1/trading/kill-switch/enable" \
  -H "X-API-Key: ${TRADING_API_KEY}" && echo
```

Expected:

- [ ] You can run this quickly if needed.

## 26. Final go/no-go decision

Go online in paper mode only if every item is true:

- [ ] DNS works for both domains.
- [ ] HTTPS works for both domains.
- [ ] API docs return `404`.
- [ ] Unauthenticated protected API calls return `401`.
- [ ] Authenticated dashboard call succeeds.
- [ ] Database migrations succeeded.
- [ ] Readiness reports PostgreSQL and Redis `ok`.
- [ ] Paper signal test returns `paper_submitted` or safely `blocked`.
- [ ] Backup script created a backup file.
- [ ] Systemd service is enabled.
- [ ] Logs show no repeated errors.
- [ ] `LIVE_TRADING_ENABLED=false`.
- [ ] `PAPER_TRADING_ENABLED=true`.
- [ ] `EXCHANGE_SANDBOX=true`.
- [ ] `WORKER_STRATEGY_SCANNING_ENABLED=false`.

Do not continue if any item is false.

## 27. First hours after launch

Watch logs:

```bash
docker compose logs -f api worker
```

Check health periodically:

```bash
curl -fsS "https://${API_DOMAIN}/api/v1/health/live" && echo
curl -fsS "https://${API_DOMAIN}/api/v1/health/ready" && echo
```

Do not enable live trading today.
