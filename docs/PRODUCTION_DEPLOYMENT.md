# Production Deployment Guide

This guide explains how to run the AI-assisted futures trading bot online 24/7. The safest production posture is **paper trading first** and **live trading disabled by default**. Only enable live trading after testnet validation, monitoring, backups, and operational procedures are proven.

## 1. Deployment overview

Recommended production layout:

```text
GitHub repository
  -> VPS pulls a tagged release or protected branch
  -> Docker Compose runs API, worker, frontend, Redis optional
  -> Managed PostgreSQL stores trades/orders/risk events
  -> Managed Redis or VPS Redis stores cache/runtime state
  -> Domain points to VPS
  -> Reverse proxy terminates SSL
  -> systemd keeps Docker Compose running after reboots
  -> logs/monitoring alert you before failures become losses
```

Core services:

- `api`: FastAPI backend and dashboard API.
- `worker`: background process for future schedulers/reconciliation jobs.
- `frontend`: React/Tailwind dashboard served by Nginx.
- `postgres`: local PostgreSQL if not using managed hosting.
- `redis`: local Redis if not using managed hosting.

## 2. GitHub deployment workflow

Use GitHub as the source of truth.

1. Keep `main` protected.
2. Make changes on feature branches.
3. Open pull requests.
4. Run tests/build checks before merging.
5. Deploy only from:
   - a version tag, for example `v0.1.0`, or
   - the protected `main` branch.

On the server:

```bash
git clone https://github.com/<owner>/<repo>.git trading-bot
cd trading-bot
git checkout main
```

For repeatable releases, prefer tags:

```bash
git fetch --tags
git checkout v0.1.0
```

Never edit production code directly on the VPS. Commit changes to GitHub, review them, then pull the approved version onto the server.

## 3. Recommended VPS setup

Minimum practical VPS for early paper trading:

- 2 vCPU
- 4 GB RAM
- 50+ GB SSD
- Ubuntu 24.04 LTS or Debian 12
- Static public IPv4
- Provider firewall support

For live trading or many symbols/timeframes:

- 4+ vCPU
- 8+ GB RAM
- 100+ GB SSD
- Managed PostgreSQL
- Managed Redis
- Automated backups

Recommended providers:

- Hetzner
- DigitalOcean
- AWS Lightsail/EC2
- Google Cloud Compute Engine
- Azure VM
- Linode/Akamai

Basic server hardening:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ufw fail2ban ca-certificates gnupg
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Create a non-root deploy user:

```bash
sudo adduser deploy
sudo usermod -aG sudo deploy
```

Log in as `deploy` for the rest of the setup.

## 4. Install Docker and Docker Compose

Install Docker from the official repository:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in, then verify:

```bash
docker --version
docker compose version
```

## 5. Production environment variables

Create a production env file on the VPS:

```bash
cp .env.example .env
chmod 600 .env
```

Important: `.env` must never be committed to GitHub. Complete [ENVIRONMENT_CHECKLIST.md](ENVIRONMENT_CHECKLIST.md) and [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) before starting the bot online.

### Required application variables

For Docker-based PostgreSQL/Redis, set matching secrets:

```env
POSTGRES_DB=futures_bot
POSTGRES_USER=bot
POSTGRES_PASSWORD=<generate-a-long-random-password>
REDIS_PASSWORD=<generate-a-long-random-password>
REDIS_URL=redis://:<same-redis-password>@redis:6379/0
```


```env
APP_ENV=production
APP_NAME=AI Futures Bot
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
API_DOCS_ENABLED=false
TRADING_API_KEY=<generate-a-long-random-secret>
CORS_ALLOWED_ORIGINS=https://bot.example.com
FRONTEND_API_BASE_URL=https://api.bot.example.com
```

### Safety-first trading defaults

Live trading is disabled by default:

```env
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
PAPER_TRADING_EQUITY=10000
EXCHANGE_SANDBOX=true
```

Keep these values for the first production deployment. This lets you verify infrastructure, logs, alerts, exchange connectivity, dashboard behavior, and strategy decisions without sending live orders.

Only after testnet/paper validation should you deliberately change:

```env
LIVE_TRADING_ENABLED=true
PAPER_TRADING_ENABLED=false
EXCHANGE_SANDBOX=false
```

Use a separate pull request or audited deployment checklist for this change.

### Exchange variables

```env
EXCHANGE_NAME=bybit
BYBIT_API_KEY=
BYBIT_API_SECRET=
BINANCE_API_KEY=
BINANCE_API_SECRET=
HEDGE_MODE_ENABLED=true
```

Security recommendations:

- Use exchange sub-accounts.
- Use API keys with futures trading only.
- Disable withdrawal permissions.
- Restrict API keys by server IP if the exchange supports it.
- Use testnet keys first.
- Rotate keys immediately if logs or files are exposed.

### Risk variables

```env
MAX_LEVERAGE=10
DEFAULT_LEVERAGE=3
MAX_OPEN_TRADES=5
MAX_DAILY_LOSS_PCT=3.0
MAX_POSITION_RISK_PCT=1.0
MAX_ACCOUNT_EXPOSURE_PCT=40.0
LOSING_STREAK_COOLDOWN_MINUTES=45
EXTREME_VOLATILITY_THRESHOLD_PCT=8.0
```

For first live trading, use stricter values than your final target, for example lower leverage, lower max open trades, and lower daily loss.

### OpenAI variables

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
AI_FILTER_ENABLED=true
AI_MIN_CONFIDENCE=0.62
```

The AI filter can block trades but must not override deterministic risk rules.

### Telegram variables

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Use Telegram alerts for:

- Startup/shutdown
- Kill switch changes
- Blocked trades
- Submitted trades
- Exchange/API failures
- High drawdown/risk events

## 6. PostgreSQL hosting

### Recommended: managed PostgreSQL

For production, prefer managed PostgreSQL because it gives you backups, monitoring, patching, and easier recovery.

Good options:

- Supabase
- Neon
- AWS RDS
- Google Cloud SQL
- DigitalOcean Managed PostgreSQL
- Aiven

Set:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB_NAME
```

Checklist:

- Enable automated backups.
- Enable point-in-time recovery if available.
- Restrict network access to the VPS IP.
- Use a strong password.
- Create a dedicated database user for the bot.
- Test restore procedure before live trading.

### Alternative: local PostgreSQL in Docker

The included `docker-compose.yml` can run PostgreSQL locally. This is acceptable for early paper trading, but less ideal for live trading unless you also configure backups.

Backup example:

```bash
docker compose exec postgres pg_dump -U bot futures_bot > backups/futures_bot_$(date +%F_%H%M).sql
```

Restore example:

```bash
docker compose exec -T postgres psql -U bot futures_bot < backups/futures_bot_YYYY-MM-DD_HHMM.sql
```

## 7. Redis hosting

Redis stores cache/runtime state such as dashboard snapshots, cooldowns, locks, and future worker coordination.

### Recommended options

- Managed Redis from your VPS/cloud provider
- Upstash Redis
- Aiven Redis
- Redis Cloud

Set:

```env
REDIS_URL=redis://USER:PASSWORD@HOST:6379/0
```

If the provider uses TLS, use the provider-specific URL format, often:

```env
REDIS_URL=rediss://USER:PASSWORD@HOST:6379/0
```

### Local Redis in Docker

Local Redis is fine for early deployment:

```env
REDIS_URL=redis://redis:6379/0
```

If running publicly, never expose Redis directly to the internet.

## 8. Docker deployment

From the project root on the VPS:

```bash
docker compose pull
docker compose build
docker compose up -d
```

Run migrations:

```bash
docker compose exec api alembic upgrade head
```

Check services:

```bash
docker compose ps
docker compose logs -f api
```

Verify health:

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{"status":"ok"}
```

## 9. Domain setup

Buy or configure a domain, for example:

```text
bot.example.com
```

Create DNS records:

```text
Type: A
Name: bot
Value: <VPS_PUBLIC_IP>
TTL: 300
```

Optional IPv6:

```text
Type: AAAA
Name: bot
Value: <VPS_IPV6>
TTL: 300
```

Wait for DNS propagation, then test:

```bash
dig bot.example.com
```

## 10. Reverse proxy and SSL

The API is protected by the `TRADING_API_KEY` setting. Clients must send it in the `X-API-Key` header. Keep the API bound to localhost in Docker and expose it only through your reverse proxy.



Use Nginx or Caddy in front of the API/frontend.

### Option A: Caddy, easiest SSL

Install Caddy:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

Example `/etc/caddy/Caddyfile`:

```caddyfile
bot.example.com {
    reverse_proxy localhost:5173
}

api.bot.example.com {
    reverse_proxy localhost:8000
}
```

Reload:

```bash
sudo systemctl reload caddy
```

Caddy automatically issues and renews Let’s Encrypt certificates.

### Option B: Nginx + Certbot

Install:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Example Nginx site:

```nginx
server {
    server_name bot.example.com;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    server_name api.bot.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable SSL:

```bash
sudo certbot --nginx -d bot.example.com -d api.bot.example.com
```

## 11. Keep the bot running permanently

Docker Compose uses `restart: unless-stopped` for services, so containers restart if they crash or if the VPS reboots after Docker starts.

For stronger control, create a systemd unit.

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=AI Futures Trading Bot
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/deploy/trading-bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

Check status:

```bash
sudo systemctl status trading-bot
```

## 12. Logs and monitoring

### Docker logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f frontend
```

Recent logs:

```bash
docker compose logs --tail=200 api
```

### System logs

```bash
journalctl -u trading-bot -f
journalctl -u docker -f
```

### Recommended monitoring

At minimum monitor:

- API health endpoint
- Container restarts
- VPS CPU/RAM/disk
- PostgreSQL connection failures
- Redis connection failures
- Exchange API failures
- Open positions
- Daily realized/unrealized PnL
- Max drawdown
- Kill switch state
- Last strategy scan time
- Telegram alert delivery

Recommended tools:

- Uptime Kuma for uptime checks
- Grafana + Prometheus for metrics
- Loki or Vector for logs
- Sentry for backend exceptions
- Provider monitoring for CPU/RAM/disk
- Telegram alerts for urgent bot events

Add an external uptime check for:

```text
https://api.bot.example.com/api/v1/health
```

## 13. Paper trading first

Before live trading, run paper/testnet mode through real market conditions.

Use:

```env
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
```

Paper trading checklist:

- API starts cleanly.
- Dashboard loads.
- Database migrations succeed.
- Strategy signals are generated as expected.
- AI filter blocks low-quality trades.
- Risk rules block excessive leverage/exposure.
- Kill switch blocks all new trades.
- Telegram alerts are delivered.
- Logs contain enough detail for debugging.
- Restarting the VPS does not lose important state.
- Backups are running and restorable.

Only continue after paper trading behavior matches expectations.

## 14. Live trading disabled by default

This project defaults to:

```env
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
```

With these settings, the trading engine returns `paper_submitted` instead of submitting real exchange orders.

To enable live trading, all of these must be deliberate:

```env
LIVE_TRADING_ENABLED=true
PAPER_TRADING_ENABLED=false
EXCHANGE_SANDBOX=false
```

Also verify:

- API keys are live keys, not testnet keys.
- Withdrawal permission is disabled.
- Max leverage is conservative.
- Max daily loss is conservative.
- Kill switch endpoint is tested.
- Telegram alerts are working.
- You have exchange web/mobile access ready for manual intervention.

## 15. Safe update procedure

Use a repeatable update flow.

1. Review and merge a pull request in GitHub.
2. Tag the release if desired:

```bash
git tag v0.1.1
git push origin v0.1.1
```

3. On the VPS, pull the approved version:

```bash
cd /home/deploy/trading-bot
git fetch origin main
git checkout main
git pull origin main
```

Or deploy a tag:

```bash
git fetch --tags
git checkout v0.1.1
```

4. Backup the database before migrations:

```bash
mkdir -p backups
docker compose exec postgres pg_dump -U bot futures_bot > backups/pre_update_$(date +%F_%H%M).sql
```

5. Build new images:

```bash
docker compose build
```

6. Run migrations:

```bash
docker compose run --rm api alembic upgrade head
```

7. Restart services:

```bash
docker compose up -d
```

8. Verify:

```bash
docker compose ps
curl https://api.bot.example.com/api/v1/health/ready
docker compose logs --tail=200 api
```

9. Keep live trading disabled during the first minutes after deployment unless the release specifically requires live mode.

Rollback procedure:

```bash
git checkout <previous_tag_or_commit>
docker compose build
docker compose up -d
```

If a migration changed the database, restore from the backup only after understanding the migration impact.

## 16. Operational safety checklist

Before 24/7 production:

- [ ] `LIVE_TRADING_ENABLED=false` for first deployment.
- [ ] Paper trading works end-to-end.
- [ ] Exchange keys have no withdrawal permission.
- [ ] API keys are IP-restricted if supported.
- [ ] PostgreSQL backups are enabled and restore-tested.
- [ ] Redis is private or managed.
- [ ] Domain uses HTTPS.
- [ ] Firewall only exposes SSH, HTTP, and HTTPS.
- [ ] Kill switch endpoint is tested.
- [ ] Telegram alerts are tested.
- [ ] Monitoring checks API health externally.
- [ ] Logs are reviewed after restart.
- [ ] Safe update/rollback procedure is documented.

## 17. Emergency actions

If something looks wrong:

1. Enable the kill switch:

```bash
curl -X POST https://api.bot.example.com/api/v1/trading/kill-switch/enable
```

2. Stop containers if needed:

```bash
docker compose down
```

3. Manually check open positions directly on the exchange.
4. Revoke API keys if compromise is suspected.
5. Preserve logs and database state for investigation.

## 18. Final recommendation

Run this stack in paper/testnet mode first, collect logs and trade decisions, compare bot behavior against your manual expectations, and only then enable live trading with small size and conservative limits.
