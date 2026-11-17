"""병원 계정·예약·답장·사후관리 (tenants, staff_users, booking_requests, booking_events, replies,
aftercare_threads, aftercare_messages) — B 모델(#28), 리비전은 A (AGENTS.md 4절)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17

- 모델: backend/src/modules/tenant·booking·aftercare/models.py (B). 상태에 visited·no_show 포함 (결정 19)
- tenants.hospital_id·booking_requests.hospital_id → hospitals.id FK (0006). 병원 행은 지우지 않으므로 삭제 동작 없음
- 탈퇴(결정 15): booking_requests.patient_id는 SET NULL (병원 쪽 기록은 남김)
- 모델과 같은지는 backend/tests/test_migrations.py가 확인
Supabase: 테이블마다 RLS를 켜고 정책은 만들지 않음 (0001과 같음)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("tenants", "staff_users", "booking_requests", "booking_events", "replies",
          "aftercare_threads", "aftercare_messages")
TS = sa.DateTime(timezone=True)
JSONT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
BIGID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
NOW = sa.func.now()
FALSE = sa.text("false")

STATUSES = ("pending", "proposed", "confirmed", "rejected", "cancelled", "expired", "visited", "no_show")
LANGS = ("ko", "en", "zh-TW", "zh-CN", "vi")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN (" + ", ".join(f"'{x}'" for x in values) + ")"


def _fk(table: str, col: str, ref: str, ondelete: str | None = None) -> sa.ForeignKey:
    ref_table = ref.split(".")[0]
    return sa.ForeignKey(ref, ondelete=ondelete, name=f"fk_{table}_{col}_{ref_table}")


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hospital_id", sa.BigInteger(), _fk("tenants", "hospital_id", "hospitals.id"), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("registration_no", sa.String(40)),
        sa.Column("requests_enabled", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("aftercare_enabled", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("joined_at", TS, nullable=False, server_default=NOW),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
    )
    op.create_index("uq_tenants_hospital", "tenants", ["hospital_id"], unique=True)

    op.create_table(
        "staff_users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), _fk("staff_users", "tenant_id", "tenants.id", "CASCADE"), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False, server_default="staff"),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.Column("disabled_at", TS),
        sa.CheckConstraint(_in("role", ("owner", "staff")), name="ck_staff_users_role"),
    )
    op.create_index("uq_staff_users_email", "staff_users", ["email"], unique=True)
    op.create_index("ix_staff_users_tenant", "staff_users", ["tenant_id"])

    op.create_table(
        "booking_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), _fk("booking_requests", "patient_id", "patients.id", "SET NULL")),
        sa.Column("tenant_id", sa.Uuid(), _fk("booking_requests", "tenant_id", "tenants.id", "CASCADE"),
                  nullable=False),
        sa.Column("hospital_id", sa.BigInteger(), _fk("booking_requests", "hospital_id", "hospitals.id"),
                  nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("lang", sa.String(8), nullable=False),
        sa.Column("nationality", sa.String(2), nullable=False),
        sa.Column("contact_method", sa.String(20), nullable=False),
        sa.Column("preferred_slots", JSONT, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("department_code", sa.String(30), nullable=False),
        sa.Column("treatment", sa.String(60)),
        sa.Column("visa_needed", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("message_original", sa.Text()),
        sa.Column("message_translated", sa.Text()),
        sa.Column("health_info", sa.Text()),
        sa.Column("patient_timezone", sa.String(64), nullable=False, server_default="Asia/Seoul"),
        sa.Column("channel", sa.String(20), nullable=False, server_default="direct"),
        sa.Column("confirmed_slot", TS),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.Column("updated_at", TS, nullable=False, server_default=NOW),
        sa.CheckConstraint(_in("status", STATUSES), name="ck_booking_requests_status"),
        sa.CheckConstraint(_in("lang", LANGS), name="ck_booking_requests_lang"),
    )
    op.create_index("ix_booking_requests_tenant_created", "booking_requests", ["tenant_id", "created_at"])
    op.create_index("ix_booking_requests_tenant_status", "booking_requests", ["tenant_id", "status"])
    op.create_index("ix_booking_requests_patient", "booking_requests", ["patient_id", "created_at"])

    op.create_table(
        "booking_events",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("request_id", sa.Uuid(),
                  _fk("booking_events", "request_id", "booking_requests.id", "CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(12)),
        sa.Column("to_status", sa.String(12), nullable=False),
        sa.Column("actor_type", sa.String(8), nullable=False),
        sa.Column("actor_id", sa.String(64)),
        sa.Column("proposed_slot", TS),
        sa.Column("reason", sa.String(20)),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.CheckConstraint(_in("to_status", STATUSES), name="ck_booking_events_to_status"),
        sa.CheckConstraint(_in("actor_type", ("patient", "staff", "system")), name="ck_booking_events_actor_type"),
    )
    op.create_index("ix_booking_events_request", "booking_events", ["request_id", "created_at"])
    op.create_index("ix_booking_events_to_status_created", "booking_events", ["to_status", "created_at"])

    op.create_table(
        "replies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request_id", sa.Uuid(), _fk("replies", "request_id", "booking_requests.id", "CASCADE"),
                  nullable=False),
        sa.Column("kind", sa.String(10), nullable=False, server_default="free"),
        sa.Column("text_ko", sa.Text(), nullable=False),
        sa.Column("text_translated", sa.Text()),
        sa.Column("ai_draft", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("approved_by", sa.Uuid(), _fk("replies", "approved_by", "staff_users.id", "SET NULL")),
        sa.Column("sent_at", TS),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.CheckConstraint(_in("kind", ("template", "free")), name="ck_replies_kind"),
    )
    op.create_index("ix_replies_request", "replies", ["request_id", "created_at"])

    op.create_table(
        "aftercare_threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request_id", sa.Uuid(),
                  _fk("aftercare_threads", "request_id", "booking_requests.id", "CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), _fk("aftercare_threads", "tenant_id", "tenants.id", "CASCADE"),
                  nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="new"),
        sa.Column("tags", JSONT, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("summary", sa.Text()),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.Column("last_message_at", TS, nullable=False, server_default=NOW),
        sa.Column("resolved_at", TS),
        sa.CheckConstraint(_in("status", ("new", "in_progress", "resolved")), name="ck_aftercare_threads_status"),
    )
    op.create_index("uq_aftercare_threads_request", "aftercare_threads", ["request_id"], unique=True)
    op.create_index("ix_aftercare_threads_tenant", "aftercare_threads", ["tenant_id", "last_message_at"])

    op.create_table(
        "aftercare_messages",
        sa.Column("id", BIGID, sa.Identity(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(),
                  _fk("aftercare_messages", "thread_id", "aftercare_threads.id", "CASCADE"), nullable=False),
        sa.Column("sender", sa.String(8), nullable=False),
        sa.Column("staff_id", sa.Uuid(), _fk("aftercare_messages", "staff_id", "staff_users.id", "SET NULL")),
        sa.Column("text_original", sa.Text(), nullable=False),
        sa.Column("text_translated", sa.Text()),
        sa.Column("has_photo", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("created_at", TS, nullable=False, server_default=NOW),
        sa.CheckConstraint(_in("sender", ("patient", "staff")), name="ck_aftercare_messages_sender"),
    )
    op.create_index("ix_aftercare_messages_thread", "aftercare_messages", ["thread_id", "created_at"])

    if op.get_bind().dialect.name == "postgresql":
        for t in TABLES:
            op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for t in reversed(TABLES):
        op.drop_table(t)
