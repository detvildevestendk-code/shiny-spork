"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-23
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategies",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "trades",
        sa.Column("exchange", sa.String(length=30), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("exit_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("stop_loss", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("take_profit", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("trailing_stop_pct", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("fees", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trades_status"), "trades", ["status"], unique=False)
    op.create_index(op.f("ix_trades_symbol"), "trades", ["symbol"], unique=False)
    op.create_table(
        "ai_decisions",
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("reasons", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_decisions_symbol"), "ai_decisions", ["symbol"], unique=False)
    op.create_table(
        "risk_events",
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_events_event_type"), "risk_events", ["event_type"], unique=False)
    op.create_table(
        "bot_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "orders",
        sa.Column("trade_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("exchange_order_id", sa.String(length=100), nullable=True),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("position_side", sa.String(length=10), nullable=False),
        sa.Column("order_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("stop_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("reduce_only", sa.Boolean(), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_exchange_order_id"), "orders", ["exchange_order_id"], unique=False)
    op.create_index(op.f("ix_orders_symbol"), "orders", ["symbol"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_symbol"), table_name="orders")
    op.drop_index(op.f("ix_orders_exchange_order_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_table("bot_settings")
    op.drop_index(op.f("ix_risk_events_event_type"), table_name="risk_events")
    op.drop_table("risk_events")
    op.drop_index(op.f("ix_ai_decisions_symbol"), table_name="ai_decisions")
    op.drop_table("ai_decisions")
    op.drop_index(op.f("ix_trades_symbol"), table_name="trades")
    op.drop_index(op.f("ix_trades_status"), table_name="trades")
    op.drop_table("trades")
    op.drop_table("strategies")
