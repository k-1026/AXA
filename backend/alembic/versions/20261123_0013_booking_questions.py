"""방문 전 환자 질문 (booking_questions)

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-23

- 결정 32: 예약 요청 뒤 방문 전까지 환자가 병원에 묻는 글 (챗봇은 초안만, 환자가 보냄)
- 백엔드만 읽고 씀 → RLS 켜고 정책 없음
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "booking_questions",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("request_id", sa.Uuid(),
                  sa.ForeignKey("booking_requests.id", name="fk_booking_questions_request_id_booking_requests",
                                ondelete="CASCADE"),
                  nullable=False),
        sa.Column("text_original", sa.Text(), nullable=False),
        sa.Column("text_translated", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_booking_questions_request", "booking_questions", ["request_id", "created_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE booking_questions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_booking_questions_request", table_name="booking_questions")
    op.drop_table("booking_questions")
