"""병원 상세 페이지 조회 기록 page_events

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-27

- 병원 대시보드 "상세페이지 방문자" 숫자 (전에는 테이블이 없어 "집계 전"). 화면이 상세 페이지를 열 때 POST /hospitals/page-views
- 개인정보 없음: 환자 id·IP·기기 정보 X. visitor_key는 브라우저 무작위 값(하루마다 바뀜)
- 같은 병원·방문자·한국 날짜는 한 줄만 (유니크) → 줄 수 = 날마다 다른 방문자 수의 합
- 모델: backend/src/modules/pageview/models.py `PageEvent`. Supabase에서는 RLS만 켬 (정책 없음 = 서버만 읽고 씀)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | Sequence[str] | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "page_events",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("hospital_id", BIGID,
                  sa.ForeignKey("hospitals.id", name="fk_page_events_hospital_id_hospitals", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("visitor_key", sa.String(64), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("lang", sa.String(8)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('view')", name="ck_page_events_type"),
        sa.UniqueConstraint("hospital_id", "type", "visitor_key", "day", name="uq_page_events_once_a_day"),
    )
    op.create_index("ix_page_events_hospital_day", "page_events", ["hospital_id", "day"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE page_events ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_page_events_hospital_day", table_name="page_events")
    op.drop_table("page_events")
