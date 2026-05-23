# AI-Assisted Crypto Futures Trading Bot

Professional starter scaffold for a Python/FastAPI crypto futures trading bot with CCXT exchange integrations, PostgreSQL persistence, Redis caching, Telegram notifications, OpenAI-based trade filtering, Docker deployment, and a React/Tailwind dashboard.

> Safety note: this is an initial architecture and implementation scaffold. Do not connect real funds until exchange-specific behavior, persistence, reconciliation, tests, alerting, and operational controls are fully validated on testnets.

## Features included

- Futures trading engine for long/short hedge-mode workflows.
- CCXT adapter for Bybit and Binance futures.
- Market, limit, and stop order request models.
- Adjustable leverage with max leverage enforcement.
- Stop-loss, take-profit, and trailing-stop fields in trade signals/schema.
- Max daily loss, max open trades, exposure caps, risk-based position sizing, and losing-streak cooldown.
- Emergency kill switch, API failure tracking, liquidation proximity checks, and extreme-volatility blocking.
- OpenAI trade filter for sentiment, volatility, news/risk detection, and confidence scoring.
- Modular strategy engine with EMA crossover and RSI divergence examples.
- Backtesting engine with trade logs, CSV export, win rate, drawdown, net PnL, and Sharpe ratio.
- PostgreSQL schema via Alembic.
- Redis client placeholder for caching and runtime coordination.
- Telegram notifier.
- React/Tailwind dashboard starter ready to call the FastAPI API.
- Docker Compose for API, worker, frontend, PostgreSQL, and Redis.

## Quick start

```bash
cp .env.example .env
# Fill exchange, OpenAI, and Telegram credentials in .env.
docker compose up --build
```

Run migrations:

```bash
docker compose exec api alembic upgrade head
```

Open:

- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/v1/health>
- Dashboard: <http://localhost:5173>

## Local backend development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Local frontend development

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

Copy `.env.example` and configure:

- `DATABASE_URL`, `REDIS_URL`
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `AI_MIN_CONFIDENCE`
- `EXCHANGE_NAME`, `BYBIT_API_KEY`, `BYBIT_API_SECRET`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- `EXCHANGE_SANDBOX`, `HEDGE_MODE_ENABLED`
- Risk limits such as `MAX_LEVERAGE`, `MAX_DAILY_LOSS_PCT`, `MAX_OPEN_TRADES`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Example signal processing request

```bash
curl -X POST "http://localhost:8000/api/v1/trading/signals/process" \
  -H "Content-Type: application/json" \
  -d '{
    "signal": {
      "strategy_name": "ema_crossover",
      "symbol": "BTC/USDT:USDT",
      "action": "open_long",
      "confidence": 0.68,
      "entry_price": 68000,
      "stop_loss": 67184,
      "take_profit": 69632,
      "trailing_stop_pct": 0.8,
      "leverage": 3,
      "reason": "Fast EMA crossed above slow EMA"
    },
    "market": {
      "symbol": "BTC/USDT:USDT",
      "timeframe": "5m",
      "close": 68000,
      "volume": 1200,
      "volatility_pct": 2.1,
      "trend_strength": 0.42
    }
  }'
```

## Documentation

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the folder structure, component responsibilities, database schema, and production hardening backlog.
