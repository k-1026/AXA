"""병원(직원) 알림 staff_notifications + Supabase Realtime

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-27

- 환자가 요청·취소·수락·질문·사후관리 글을 보내면 그 병원(tenant)에 한 줄 → 대시보드가 Realtime으로 받아 바로 다시 불러옴
  (전에는 대시보드가 30초마다 확인해서 새 요청이 최대 30초 늦게 보였음)
- 모델: backend/src/modules/notification/models.py `StaffNotification`. 글·건강정보 없이 종류·요청서 id·상태 코드만
- Supabase(Postgres)에서만: RLS 켜고 "자기 병원 알림만 읽기" 정책 (토큰의 tenant_id 클레임 = tenant_id,
  백엔드가 SUPABASE_JWT_SECRET으로 발급 — POST /tenant/notifications/realtime-token), authenticated 역할에 SELECT,
  Realtime 발행(supabase_realtime)에 추가. 역할·발행이 없는 일반 Postgres면 건너뜀 (0010 notifications와 같은 방식)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

SUPABASE_ONLY = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT SELECT ON staff_notifications TO authenticated;
    CREATE POLICY staff_notifications_own_tenant ON staff_notifications FOR SELECT TO authenticated
      USING (tenant_id::text = (auth.jwt() ->> 'tenant_id'));
  END IF;
  IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE staff_notifications;
  END IF;
END $$;
"""

SUPABASE_ONLY_DOWN = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'staff_notifications') THEN
    ALTER PUBLICATION supabase_realtime DROP TABLE staff_notifications;
  END IF;
END $$;
"""


def upgrade() -> None:
    op.create_table(
        "staff_notifications",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(),
                  sa.ForeignKey("tenants.id", name="fk_staff_notifications_tenant_id_tenants", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("request_id", sa.Uuid(),
                  sa.ForeignKey("booking_requests.id", name="fk_staff_notifications_request_id_booking_requests",
                                ondelete="CASCADE"),
                  nullable=False),
        sa.Column("status", sa.String(12)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('request', 'status', 'question', 'aftercare')", name="ck_staff_notifications_kind"),
    )
    op.create_index("ix_staff_notifications_tenant", "staff_notifications", ["tenant_id", "created_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE staff_notifications ENABLE ROW LEVEL SECURITY")
        op.execute(SUPABASE_ONLY)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(SUPABASE_ONLY_DOWN)
    op.drop_index("ix_staff_notifications_tenant", table_name="staff_notifications")
    op.drop_table("staff_notifications")
