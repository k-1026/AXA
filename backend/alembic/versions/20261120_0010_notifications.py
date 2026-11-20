"""사이트 안 알림 (notifications) + Supabase Realtime

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-20

- 모델: backend/src/modules/notification/models.py (A, 결정 27). 글·건강정보 없이 종류·요청서 id·상태 코드만
- Supabase(Postgres)에서만: RLS 켜고 "자기 알림만 읽기" 정책 (토큰 sub = patient_id, 백엔드가 SUPABASE_JWT_SECRET으로 발급),
  authenticated 역할에 SELECT, Realtime 발행(supabase_realtime)에 추가. 역할·발행이 없는 일반 Postgres면 건너뜀
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

SUPABASE_ONLY = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT SELECT ON notifications TO authenticated;
    CREATE POLICY notifications_own ON notifications FOR SELECT TO authenticated
      USING (patient_id::text = (auth.jwt() ->> 'sub'));
  END IF;
  IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE notifications;
  END IF;
END $$;
"""

SUPABASE_ONLY_DOWN = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'notifications') THEN
    ALTER PUBLICATION supabase_realtime DROP TABLE notifications;
  END IF;
END $$;
"""


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(),
                  sa.ForeignKey("patients.id", name="fk_notifications_patient_id_patients", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("request_id", sa.Uuid(),
                  sa.ForeignKey("booking_requests.id", name="fk_notifications_request_id_booking_requests",
                                ondelete="CASCADE"),
                  nullable=False),
        sa.Column("status", sa.String(12)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN ('status', 'reply', 'aftercare')", name="ck_notifications_kind"),
    )
    op.create_index("ix_notifications_patient", "notifications", ["patient_id", "created_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
        op.execute(SUPABASE_ONLY)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(SUPABASE_ONLY_DOWN)
    op.drop_index("ix_notifications_patient", table_name="notifications")
    op.drop_table("notifications")
