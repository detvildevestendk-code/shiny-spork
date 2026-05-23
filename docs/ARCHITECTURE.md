# Architecture

This repository is a production-oriented starter for an AI-assisted crypto futures trading bot. The AI layer is deliberately constrained: it can block trades or lower confidence, but it cannot submit orders, increase leverage, move stops, or override deterministic risk controls.

## Runtime components

- **FastAPI API**: exposes health checks, dashboard data, strategy metadata, trading signal processing, position close actions, and kill-switch controls.
- **Trading engine**: coordinates safety checks, risk checks, AI filtering, position sizing, and exchange order placement.
- **Exchange adapters**: CCXT-based abstraction for Bybit and Binance futures with hedge-mode support.
- **Risk manager**: enforces max leverage, max open trades, max daily loss, risk-based sizing, exposure caps, and losing-streak cooldowns.
- **Safety controller**: kill switch, API failure detection, liquidation proximity checks, and extreme-volatility auto-disable.
- **AI filter**: OpenAI-backed sentiment, volatility, news/risk, and confidence scoring. It only returns pass/block decisions.
- **Strategy engine**: modular Freqtrade-compatible style with pandas candle input and strategy signal output.
- **Backtesting**: runs historical candle simulations, logs trades, exports CSV, and reports win rate, drawdown, net PnL, and Sharpe ratio.
- **Persistence**: PostgreSQL stores trades, orders, AI decisions, risk events, bot settings, and strategy configs.
- **Cache**: Redis is available for market snapshots, dashboard state, cooldown state, and reconciliation locks.
- **Notifications**: Telegram notifier for execution, safety, and risk alerts.
- **Dashboard**: React/Tailwind starter that is API-ready for PnL, positions, risk exposure, AI score, connection status, strategy toggles, and Telegram settings.

## Trade decision flow

1. Strategy generates a `StrategySignal`.
2. Safety controller checks kill switch, API failures, liquidation risk, and extreme volatility.
3. Risk manager checks deterministic limits and calculates position size.
4. AI filter analyzes sentiment/news/volatility and can block low-confidence trades.
5. Trading engine builds an exchange order using the risk-approved size and configured leverage.
6. Exchange adapter submits the CCXT futures order.
7. Persistence/notifications can be added around the execution result for auditability.

## Folder structure

```text
.
├── backend
│   ├── app
│   │   ├── ai                 # OpenAI market analyzer and trade filter
│   │   ├── api                # FastAPI routers and dependencies
│   │   ├── backtesting        # Historical simulation and metrics
│   │   ├── cache              # Redis client
│   │   ├── core               # Settings and logging
│   │   ├── db                 # SQLAlchemy models and sessions
│   │   ├── exchanges          # CCXT futures adapters
│   │   ├── notifications      # Telegram integration
│   │   ├── strategies         # Modular strategies
│   │   └── trading            # Engine, risk, safety, schemas
│   ├── migrations             # Alembic migrations
│   ├── Dockerfile
│   └── requirements.txt
├── docs
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.sql
│   ├── ENVIRONMENT_CHECKLIST.md
│   ├── PRE_DEPLOYMENT_CHECKLIST.md
│   └── PRODUCTION_DEPLOYMENT.md
├── frontend                  # React/Tailwind dashboard starter
├── docker-compose.yml
├── .env.example
└── README.md
```

## Database schema

The initial Alembic migration creates:

- `strategies`: enabled flags and per-strategy JSON configuration.
- `trades`: lifecycle, side, leverage, sizing, stops, take-profit, trailing stop, PnL, and metadata.
- `orders`: exchange order IDs, order type, hedge side, reduce-only flag, and raw exchange response.
- `ai_decisions`: model name, confidence, pass/block decision, reasons, and prompt payload.
- `risk_events`: safety/risk incidents such as kill switch, API failures, volatility disables, and liquidation risk.
- `bot_settings`: dashboard-editable settings in JSON.

## Strategy contract

Strategies inherit from `app.strategies.base.Strategy` and implement:

```python
def generate_signal(self, symbol: str, candles: pd.DataFrame) -> StrategySignal:
    ...
```

Candles should contain `timestamp`, `open`, `high`, `low`, `close`, and `volume`. This mirrors Freqtrade-style dataframe strategies while keeping the execution engine independent from Freqtrade internals.

## Production hardening backlog

- Persist every decision and order before/after exchange submission.
- Add exchange reconciliation jobs for fills, partial fills, funding, and position drift.
- Add authenticated API users and role-based dashboard access.
- Add websocket market data collectors.
- Implement stop-loss/take-profit/trailing-stop order reconciliation per exchange.
- Add robust alert routing and incident severity policies.
- Add integration tests against exchange testnets.
