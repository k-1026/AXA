"""병원 공공정보 (hospitals, departments, hospital_departments, hospital_hours)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-16

- docs/backend-db-schema.md 2절. 채우기: backend/scripts/load_hospitals.py (ykiho로 upsert, 행 삭제 X)
- 스키마에 더한 칸: type_name_ko(종별 이름), hospital_hours.day_order(요일 정렬)
- is_registered_facility = 외국인환자 유치의료기관 등록. 상담·예약 요청은 이 병원만 (compliance 2-1)
Supabase: 테이블마다 RLS를 켜고 정책은 만들지 않음 (0001과 같음)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("hospitals", "departments", "hospital_departments", "hospital_hours")
TS = sa.DateTime(timezone=True)
# SQLite(로컬 확인용)는 BIGINT PK에 자동 번호를 안 붙임 → INTEGER로
BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "hospitals",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("ykiho", sa.String(200), nullable=False),
        sa.Column("name_ko", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200)),
        sa.Column("type_code", sa.String(4)),
        sa.Column("type_name_ko", sa.String(40)),
        sa.Column("sggu", sa.String(40)),
        sa.Column("addr_ko", sa.String(400)),
        sa.Column("addr_en", sa.String(400)),
        sa.Column("tel", sa.String(40)),
        sa.Column("lat", sa.Float()),
        sa.Column("lng", sa.Float()),
        sa.Column("homepage", sa.String(400)),
        sa.Column("is_registered_facility", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status_verdict", sa.String(10), nullable=False, server_default="normal"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("fetched_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.UniqueConstraint("ykiho", name="uq_hospitals_ykiho"),
        sa.CheckConstraint("status_verdict IN ('normal','closed','unknown')", name="ck_hospitals_status_verdict"),
    )
    op.create_index("ix_hospitals_sggu", "hospitals", ["sggu"])
    op.create_table(
        "departments",
        sa.Column("code", sa.String(30), primary_key=True),
        sa.Column("hira_code", sa.String(4)),
    )
    op.create_table(
        "hospital_departments",
        sa.Column("hospital_id", BIGID, sa.ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("dept_code", sa.String(30), sa.ForeignKey("departments.code"), primary_key=True),
    )
    op.create_table(
        "hospital_hours",
        sa.Column("hospital_id", BIGID, sa.ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.String(3), primary_key=True),
        sa.Column("day_order", sa.Integer(), nullable=False),
        sa.Column("open_time", sa.Time()),
        sa.Column("close_time", sa.Time()),
        sa.Column("lunch_start", sa.Time()),
        sa.Column("lunch_end", sa.Time()),
        sa.Column("memo_ko", sa.String(200)),
        sa.Column("state", sa.String(10), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("checked_at", TS, nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        for t in TABLES:
            op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for t in reversed(TABLES):
        op.drop_table(t)
