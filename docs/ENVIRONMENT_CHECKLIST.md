# Environment Deployment Checklist

Use this checklist after copying `.env.example` to `.env` and before starting the bot online.

```bash
cp .env.example .env
chmod 600 .env
```

Every `CHANGE_ME_*` value must be replaced. Do not deploy with placeholder values.

## 1. Required application settings

- [ ] `APP_ENV=production`
- [ ] `APP_NAME` is the display name you want.
- [ ] `LOG_LEVEL=INFO` for normal production use.
- [ ] `TRADING_API_KEY` is set to a long random secret.
  - Generate one with: `openssl rand -hex 32`
  - Clients must send it as: `X-API-Key: <value>`
- [ ] `CORS_ALLOWED_ORIGINS` contains only your trusted dashboard origin.
  - Example: `https://bot.example.com`
  - Do not use `*` in production.
- [ ] `FRONTEND_API_BASE_URL` points to your public API URL.
  - Example: `https://api.example.com`

## 2. Required PostgreSQL settings

Choose one option.

### Option A: Docker Compose PostgreSQL

- [ ] `POSTGRES_DB=futures_bot` or your chosen DB name.
- [ ] `POSTGRES_USER=bot` or your chosen DB user.
- [ ] `POSTGRES_PASSWORD` is a long random secret.
  - Generate one with: `openssl rand -hex 32`
- [ ] `DATABASE_URL` uses the same DB user/password/name:

```env
DATABASE_URL=postgresql+asyncpg://bot:<POSTGRES_PASSWORD>@postgres:5432/futures_bot
```

### Option B: Managed PostgreSQL

- [ ] Managed PostgreSQL instance is created.
- [ ] Automated backups are enabled.
- [ ] Network access is restricted to the VPS IP if supported.
- [ ] Dedicated DB user is created for the bot.
- [ ] `DATABASE_URL` is set to the managed connection string:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB_NAME
```

- [ ] You verified migrations can run:

```bash
docker compose exec api alembic upgrade head
```

## 3. Required Redis settings

Choose one option.

### Option A: Docker Compose Redis

- [ ] `REDIS_PASSWORD` is a long random secret.
  - Generate one with: `openssl rand -hex 32`
- [ ] `REDIS_URL` uses that password:

```env
REDIS_URL=redis://:<REDIS_PASSWORD>@redis:6379/0
```

### Option B: Managed Redis

- [ ] Managed Redis instance is created.
- [ ] Redis is not publicly accessible without authentication.
- [ ] TLS is enabled if your provider supports/requires it.
- [ ] `REDIS_URL` is set correctly:

```env
REDIS_URL=rediss://USER:PASSWORD@HOST:6379/0
```

## 4. Paper trading safety settings

These must stay exactly like this for first deployment:

- [ ] `LIVE_TRADING_ENABLED=false`
- [ ] `PAPER_TRADING_ENABLED=true`
- [ ] `EXCHANGE_SANDBOX=true`
- [ ] `PAPER_TRADING_EQUITY` is set to your simulated account size.

Do not enable live trading in the first online deployment.

## 5. Exchange credentials

For paper/testnet validation:

- [ ] `EXCHANGE_NAME` is either `bybit` or `binance`.
- [ ] Testnet/sandbox API keys are used if you configure exchange keys.
- [ ] API keys do not have withdrawal permissions.
- [ ] API keys are IP-restricted to the VPS if the exchange supports it.
- [ ] `HEDGE_MODE_ENABLED=true` if you want simultaneous long/short support.

Fill only the keys for the exchange you use:

- [ ] Bybit: `BYBIT_API_KEY`, `BYBIT_API_SECRET`
- [ ] Binance: `BINANCE_API_KEY`, `BINANCE_API_SECRET`

## 6. AI filter settings

For paper testing:

- [ ] `AI_FILTER_ENABLED=true` if you want OpenAI analysis.
- [ ] `OPENAI_API_KEY` is set if AI filtering should call OpenAI.
- [ ] `OPENAI_MODEL` is set.
- [ ] `AI_MIN_CONFIDENCE` is set between `0` and `1`.

Notes:

- Paper mode can run without an OpenAI key.
- Live mode should not be used without AI/risk review enabled.

## 7. Risk limits

Review every limit before starting the worker:

- [ ] `MAX_LEVERAGE` is conservative.
- [ ] `DEFAULT_LEVERAGE` is lower than or equal to `MAX_LEVERAGE`.
- [ ] `MAX_OPEN_TRADES` is conservative.
- [ ] `MAX_DAILY_LOSS_PCT` is conservative.
- [ ] `MAX_POSITION_RISK_PCT` is conservative.
- [ ] `MAX_ACCOUNT_EXPOSURE_PCT` is conservative.
- [ ] `LOSING_STREAK_COOLDOWN_MINUTES` is set.
- [ ] `EXTREME_VOLATILITY_THRESHOLD_PCT` is set.

Recommended first paper deployment:

```env
MAX_LEVERAGE=3
DEFAULT_LEVERAGE=1
MAX_OPEN_TRADES=1
MAX_DAILY_LOSS_PCT=1.0
MAX_POSITION_RISK_PCT=0.25
MAX_ACCOUNT_EXPOSURE_PCT=10.0
```

## 8. Worker and strategy scanning

For first startup:

- [ ] `WORKER_STRATEGY_SCANNING_ENABLED=false`

After API, DB, Redis, dashboard, and health checks work:

- [ ] Set `TRADING_SYMBOLS` to the symbols you want.
  - Example: `BTC/USDT:USDT,ETH/USDT:USDT`
- [ ] Set `ENABLED_STRATEGIES` to known registered strategy names.
  - Example: `ema_crossover,rsi_divergence`
- [ ] Set `STRATEGY_SCAN_INTERVAL_SECONDS` to a safe interval.
- [ ] Enable scanning only when ready:

```env
WORKER_STRATEGY_SCANNING_ENABLED=true
```

## 9. Telegram alerts

Recommended before any long-running paper test:

- [ ] `TELEGRAM_BOT_TOKEN` is set.
- [ ] `TELEGRAM_CHAT_ID` is set.
- [ ] Test alert delivery manually before live trading.

## 10. Domain and SSL

- [ ] Dashboard domain points to the VPS.
  - Example: `bot.example.com`
- [ ] API domain points to the VPS.
  - Example: `api.example.com`
- [ ] SSL certificate is issued with Caddy or Nginx/Certbot.
- [ ] `CORS_ALLOWED_ORIGINS` matches the dashboard HTTPS origin.
- [ ] `FRONTEND_API_BASE_URL` matches the API HTTPS origin.

## 11. Docker and network safety

- [ ] PostgreSQL is not exposed publicly.
- [ ] Redis is not exposed publicly.
- [ ] API/frontend containers bind to localhost or are behind a reverse proxy.
- [ ] Firewall allows only SSH, HTTP, and HTTPS.
- [ ] `.env` permissions are restricted with `chmod 600 .env`.

## 12. Final validation commands

Run these after filling `.env`:

```bash
docker compose config
docker compose up -d --build
docker compose exec api alembic upgrade head
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
curl -H "X-API-Key: $TRADING_API_KEY" http://localhost:8000/api/v1/dashboard/summary
```

Expected:

- [ ] Compose config renders without errors.
- [ ] API container is healthy.
- [ ] Worker container is running.
- [ ] PostgreSQL readiness is `ok`.
- [ ] Redis readiness is `ok`.
- [ ] Dashboard summary requires `X-API-Key` and returns paper-mode data.

## 13. Absolute no-go checks

Do not deploy if any of these are true:

- [ ] Any `CHANGE_ME_*` placeholder remains in `.env`.
- [ ] `TRADING_API_KEY` is empty.
- [ ] `POSTGRES_PASSWORD` is weak or unchanged.
- [ ] `REDIS_PASSWORD` is weak or unchanged.
- [ ] `CORS_ALLOWED_ORIGINS=*`.
- [ ] `LIVE_TRADING_ENABLED=true` during first deployment.
- [ ] `PAPER_TRADING_ENABLED=false` during first deployment.
- [ ] `EXCHANGE_SANDBOX=false` during first deployment.
- [ ] Exchange API keys have withdrawal permission.
- [ ] PostgreSQL or Redis ports are public on the VPS firewall.
