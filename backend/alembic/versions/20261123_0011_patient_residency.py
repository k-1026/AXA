"""환자 체류 형태 (patients.residency·residence_country·residency_answered_at)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-23

- 결정 28: 가입 때 거주국 + 3문항(외국인등록·국내거소신고·건강보험)으로 판단, 예약 요청 때 다시 확인
- 기존 계정은 NULL → 첫 예약 요청 전에 PUT /me/residency로 받음. 칸 추가만이라 기존 백엔드에는 영향 없음
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as b:
        b.add_column(sa.Column("residency", sa.String(16), nullable=True))
        b.add_column(sa.Column("residence_country", sa.String(2), nullable=True))
        b.add_column(sa.Column("residency_answered_at", sa.DateTime(timezone=True), nullable=True))
        b.create_check_constraint("ck_patients_residency", "residency IS NULL OR residency IN ('short_term', 'resident')")


def downgrade() -> None:
    with op.batch_alter_table("patients") as b:
        b.drop_constraint("ck_patients_residency", type_="check")
        b.drop_column("residency_answered_at")
        b.drop_column("residence_country")
        b.drop_column("residency")
