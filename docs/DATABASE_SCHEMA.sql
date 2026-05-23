CREATE TABLE strategies (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE trades (
    id UUID PRIMARY KEY,
    exchange VARCHAR(30) NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    side VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    leverage INTEGER NOT NULL,
    amount NUMERIC(28, 12) NOT NULL,
    entry_price NUMERIC(28, 12),
    exit_price NUMERIC(28, 12),
    stop_loss NUMERIC(28, 12),
    take_profit NUMERIC(28, 12),
    trailing_stop_pct NUMERIC(8, 4),
    realized_pnl NUMERIC(28, 12),
    fees NUMERIC(28, 12),
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    metadata_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_trades_symbol ON trades (symbol);
CREATE INDEX ix_trades_status ON trades (status);

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    trade_id UUID REFERENCES trades(id),
    exchange_order_id VARCHAR(100),
    symbol VARCHAR(30) NOT NULL,
    side VARCHAR(10) NOT NULL,
    position_side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL,
    amount NUMERIC(28, 12) NOT NULL,
    price NUMERIC(28, 12),
    stop_price NUMERIC(28, 12),
    reduce_only BOOLEAN NOT NULL DEFAULT FALSE,
    raw_response JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_orders_exchange_order_id ON orders (exchange_order_id);
CREATE INDEX ix_orders_symbol ON orders (symbol);

CREATE TABLE ai_decisions (
    id UUID PRIMARY KEY,
    symbol VARCHAR(30) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    allowed BOOLEAN NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL,
    reasons TEXT NOT NULL,
    model VARCHAR(80) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_ai_decisions_symbol ON ai_decisions (symbol);

CREATE TABLE risk_events (
    id UUID PRIMARY KEY,
    severity VARCHAR(20) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    message TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_risk_events_event_type ON risk_events (event_type);

CREATE TABLE bot_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
