"""탈퇴 = 즉시 삭제 (결정 15): patients.deleted_at 삭제, 이메일 부분 UNIQUE -> 일반 UNIQUE

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 예전 방식으로 탈퇴 표시만 된 행이 있으면 지금 규칙대로 정리 (세션 CASCADE, 동의 SET NULL)
    op.execute("DELETE FROM patients WHERE deleted_at IS NOT NULL")
    op.drop_index("uq_patients_email_live", table_name="patients")
    with op.batch_alter_table("patients") as batch:
        batch.drop_column("deleted_at")
    op.create_index("uq_patients_email", "patients", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_patients_email", table_name="patients")
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_index(
        "uq_patients_email_live",
        "patients",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
