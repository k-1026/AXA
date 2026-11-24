"""웹 푸시 구독 (push_subscriptions)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-23

- 결정 30: 사이트 안 알림이 생길 때 구독한 브라우저에 푸시 (종류·상태 코드만, 글·건강정보 X)
- 백엔드만 읽고 씀 → RLS 켜고 정책 없음 (Supabase API로는 안 보임)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(),
                  sa.ForeignKey("patients.id", name="fk_push_subscriptions_patient_id_patients", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(200), nullable=False),
        sa.Column("auth", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True)
    op.create_index("ix_push_subscriptions_patient", "push_subscriptions", ["patient_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_patient", table_name="push_subscriptions")
    op.drop_index("uq_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
