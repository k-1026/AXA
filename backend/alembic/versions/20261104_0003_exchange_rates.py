"""환율 (exchange_rates) — 가격 가이드 통화 표시, 매일 10시(KST) 적용일 기준

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exchange_rates",
        sa.Column("currency", sa.String(3), primary_key=True),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("base_date", sa.Date(), nullable=False),
        sa.Column("applied_on", sa.Date(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE exchange_rates ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("exchange_rates")
