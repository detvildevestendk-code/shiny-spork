# Pre-Deployment Checklist

Use this checklist before running the trading bot online. It complements `.env.example` and [ENVIRONMENT_CHECKLIST.md](ENVIRONMENT_CHECKLIST.md). The required first deployment posture is **paper trading only** with live trading disabled.

## 1. Repository and release readiness

- [ ] All changes are committed to Git.
- [ ] Changes were reviewed through a pull request.
- [ ] You are deploying from a known branch or tag.
- [ ] The server is not running uncommitted local edits.
- [ ] The latest deployment commit hash is recorded.
- [ ] README and deployment docs match the version being deployed.

Recommended commands on the server:

```bash
git status --short
git rev-parse --short HEAD
git branch --show-current
```

## 2. Local validation before deployment

Run these before copying the release to a VPS:

```bash
python3 -m compileall backend/app backend/migrations
cd frontend && npm install && npm run build
```

If Docker is available locally:

```bash
docker compose config
docker compose build
```

Required checks:

- [ ] Backend compiles.
- [ ] Frontend builds.
- [ ] Docker Compose config renders without errors.
- [ ] No secrets are committed.
- [ ] `.env` is not tracked by Git.

## 3. VPS/server prerequisites

- [ ] VPS has a static public IP.
- [ ] Ubuntu/Debian server is updated.
- [ ] Non-root deploy user exists.
- [ ] SSH key login works.
- [ ] Password SSH login is disabled if possible.
- [ ] Firewall allows only required ports:
  - SSH: `22`
  - HTTP: `80`
  - HTTPS: `443`
- [ ] Docker and Docker Compose are installed.
- [ ] Server time/NTP is correct.
- [ ] Disk space is sufficient for logs, Docker images, and backups.

Recommended commands:

```bash
sudo apt update && sudo apt upgrade -y
docker --version
docker compose version
timedatectl
```

## 4. Environment file readiness

- [ ] `.env.example` was copied to `.env`.
- [ ] `.env` permissions are restricted:

```bash
chmod 600 .env
```

- [ ] No `CHANGE_ME_*` placeholders remain:

```bash
if grep -n "CHANGE_ME" .env; then echo "Fix placeholders"; exit 1; fi
```

- [ ] `TRADING_API_KEY` is a long random value.
- [ ] `POSTGRES_PASSWORD` is a long random value.
- [ ] `REDIS_PASSWORD` is a long random value.
- [ ] `DATABASE_URL` matches the PostgreSQL host/user/password/db.
- [ ] `REDIS_URL` matches the Redis host/password/db.
- [ ] `CORS_ALLOWED_ORIGINS` is not `*`.
- [ ] `FRONTEND_API_BASE_URL` is the public HTTPS API URL.

See [ENVIRONMENT_CHECKLIST.md](ENVIRONMENT_CHECKLIST.md) for every `.env` variable.

## 5. Mandatory paper-trading safety flags

For first deployment, these must be set exactly:

```env
LIVE_TRADING_ENABLED=false
PAPER_TRADING_ENABLED=true
EXCHANGE_SANDBOX=true
```

Checklist:

- [ ] `LIVE_TRADING_ENABLED=false`
- [ ] `PAPER_TRADING_ENABLED=true`
- [ ] `EXCHANGE_SANDBOX=true`
- [ ] `PAPER_TRADING_EQUITY` is set to the simulated account size.
- [ ] `WORKER_STRATEGY_SCANNING_ENABLED=false` for first startup.

Do not continue if live trading is enabled.

## 6. Exchange API key safety

- [ ] First deployment uses no exchange keys or testnet/sandbox keys.
- [ ] Exchange API keys do not have withdrawal permission.
- [ ] Exchange API keys are IP-restricted to the VPS if supported.
- [ ] Separate sub-account is used if available.
- [ ] Hedge mode is enabled intentionally if needed.
- [ ] Manual exchange login is available for emergency intervention.

## 7. PostgreSQL readiness

Choose one deployment model.

### Managed PostgreSQL

- [ ] Managed database is created.
- [ ] Automated backups are enabled.
- [ ] Restore process is understood.
- [ ] Network access is restricted to the VPS IP if supported.
- [ ] Dedicated user/password is configured.
- [ ] `DATABASE_URL` uses `postgresql+asyncpg://...`.

### Docker PostgreSQL

- [ ] `POSTGRES_PASSWORD` is strong.
- [ ] PostgreSQL port is not exposed publicly.
- [ ] Docker volume `postgres_data` is used.
- [ ] Backup command is tested.

Migration check:

```bash
docker compose exec api alembic upgrade head
```

- [ ] Migrations run successfully.

## 8. Redis readiness

Choose one deployment model.

### Managed Redis

- [ ] Redis requires authentication.
- [ ] Redis is not publicly open.
- [ ] TLS URL uses `rediss://` if required by provider.
- [ ] `REDIS_URL` is correct.

### Docker Redis

- [ ] `REDIS_PASSWORD` is strong.
- [ ] Redis port is not exposed publicly.
- [ ] Redis append-only persistence is enabled.
- [ ] Docker volume `redis_data` is used.

Readiness check after startup:

```bash
curl http://localhost:8000/api/v1/health/ready
```

- [ ] Redis check returns `ok`.

## 9. Docker deployment readiness

- [ ] `docker compose config` succeeds.
- [ ] `docker compose build` succeeds.
- [ ] API binds to localhost or reverse proxy only.
- [ ] Frontend binds to localhost or reverse proxy only.
- [ ] PostgreSQL has no public port mapping.
- [ ] Redis has no public port mapping.
- [ ] Containers have restart policies.
- [ ] Containers do not require root for normal runtime.

Startup:

```bash
docker compose up -d --build
docker compose ps
```

## 10. Domain, reverse proxy, and SSL

- [ ] Dashboard DNS record points to the VPS.
- [ ] API DNS record points to the VPS.
- [ ] Reverse proxy is configured.
- [ ] SSL certificates are issued.
- [ ] HTTP redirects to HTTPS.
- [ ] API is reachable only through the intended domain.
- [ ] Dashboard uses the correct API URL.

Expected examples:

```env
CORS_ALLOWED_ORIGINS=https://bot.example.com
FRONTEND_API_BASE_URL=https://api.example.com
```

## 11. API authentication validation

After startup:

```bash
curl -i https://api.example.com/api/v1/dashboard/summary
curl -i -H "X-API-Key: $TRADING_API_KEY" https://api.example.com/api/v1/dashboard/summary
```

Required results:

- [ ] Request without `X-API-Key` returns `401` or `503` if auth is not configured.
- [ ] Request with valid `X-API-Key` succeeds.
- [ ] Kill-switch endpoints require `X-API-Key`.
- [ ] Signal-processing endpoint requires `X-API-Key`.

## 12. Health checks

Run:

```bash
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
```

Required:

- [ ] Liveness returns `ok`.
- [ ] Database readiness returns `ok`.
- [ ] Redis readiness returns `ok`.
- [ ] Worker heartbeat is present after worker startup.

## 13. Paper-trading functional test

Submit a test paper signal:

```bash
curl -X POST "$FRONTEND_API_BASE_URL/api/v1/trading/signals/process"   -H "Content-Type: application/json"   -H "X-API-Key: $TRADING_API_KEY"   -d '{
    "signal": {
      "strategy_name": "ema_crossover",
      "symbol": "BTC/USDT:USDT",
      "action": "open_long",
      "confidence": 0.7,
      "entry_price": 68000,
      "stop_loss": 67184,
      "take_profit": 69632,
      "leverage": 1,
      "reason": "paper deployment test"
    },
    "market": {
      "symbol": "BTC/USDT:USDT",
      "timeframe": "5m",
      "close": 68000,
      "volume": 1000,
      "volatility_pct": 1.5
    }
  }'
```

Required:

- [ ] Response status is `paper_submitted` or safely `blocked`.
- [ ] Response does not contain a live exchange order response.
- [ ] Dashboard/trade history shows the paper trade if submitted.
- [ ] Database contains the paper trade/order record.

## 14. Monitoring and alerts

Minimum before unattended operation:

- [ ] External uptime monitor checks `/api/v1/health/live`.
- [ ] Logs are accessible with `docker compose logs`.
- [ ] Disk usage is monitored.
- [ ] CPU and memory are monitored.
- [ ] PostgreSQL backups are monitored.
- [ ] Telegram alerts are configured or another alerting channel exists.
- [ ] You know how to enable the kill switch quickly.

Recommended kill-switch command:

```bash
curl -X POST https://api.example.com/api/v1/trading/kill-switch/enable   -H "X-API-Key: $TRADING_API_KEY"
```

## 15. Backup and rollback plan

- [ ] Database backup exists before deployment.
- [ ] Restore procedure is documented.
- [ ] Previous Git tag/commit is known.
- [ ] Rollback command is documented.
- [ ] You know whether migrations are reversible.

Example backup for Docker Postgres:

```bash
mkdir -p backups
docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backups/pre_deploy_$(date +%F_%H%M).sql
```

## 16. Final go/no-go checks

Do not deploy if any item is true:

- [ ] Any `CHANGE_ME_*` placeholder remains.
- [ ] `.env` is committed or world-readable.
- [ ] `LIVE_TRADING_ENABLED=true`.
- [ ] `PAPER_TRADING_ENABLED=false`.
- [ ] `EXCHANGE_SANDBOX=false`.
- [ ] `TRADING_API_KEY` is empty.
- [ ] API is public without authentication.
- [ ] `CORS_ALLOWED_ORIGINS=*`.
- [ ] PostgreSQL is exposed to the public internet.
- [ ] Redis is exposed to the public internet.
- [ ] Exchange API keys have withdrawal permissions.
- [ ] Backups are not configured.
- [ ] You have not tested the kill switch.

## 17. First 24/7 paper run

For the first online run:

- [ ] Keep worker strategy scanning disabled until health checks pass.
- [ ] Start containers.
- [ ] Run migrations.
- [ ] Verify API auth.
- [ ] Verify readiness.
- [ ] Submit one manual paper signal.
- [ ] Confirm dashboard/trade history updates.
- [ ] Enable worker scanning only after manual tests pass.
- [ ] Watch logs during the initial run.

Suggested startup sequence:

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose ps
docker compose logs --tail=200 api
docker compose logs --tail=200 worker
```
