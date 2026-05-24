"""add signal decisions

Revision ID: 0002_signal_decisions
Revises: 0001_initial_schema
Create Date: 2026-05-24
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_signal_decisions"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_decisions",
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("market_price", sa.Numeric(precision=28, scale=12), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_signal_decisions_symbol"), "signal_decisions", ["symbol"], unique=False)
    op.create_index(op.f("ix_signal_decisions_strategy_name"), "signal_decisions", ["strategy_name"], unique=False)
    op.create_index(op.f("ix_signal_decisions_decision"), "signal_decisions", ["decision"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_signal_decisions_decision"), table_name="signal_decisions")
    op.drop_index(op.f("ix_signal_decisions_strategy_name"), table_name="signal_decisions")
    op.drop_index(op.f("ix_signal_decisions_symbol"), table_name="signal_decisions")
    op.drop_table("signal_decisions")
