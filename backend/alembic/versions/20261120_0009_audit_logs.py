"""열람·처리 기록 (audit_logs)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-20

- 모델: backend/src/modules/audit/models.py (B 모듈, A 작성). 직원이 요청서·사후관리를 열람·답장할 때 한 줄 (결정 24)
- 내용은 저장하지 않음 (누가·어느 병원·무엇을·어떤 대상·언제)
Supabase: RLS 켜고 정책 없음 (0001과 같음)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", name="fk_audit_logs_tenant_id_tenants", ondelete="CASCADE"), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("ref", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_tenant", "audit_logs", ["tenant_id", "created_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant", table_name="audit_logs")
    op.drop_table("audit_logs")
