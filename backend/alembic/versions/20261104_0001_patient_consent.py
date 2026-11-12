"""환자 계정·로그인 세션·동의 (patients, auth_sessions, consents)

Revision ID: 0001
Revises:
Create Date: 2026-11-04

Supabase: 테이블마다 RLS를 켜고 정책은 만들지 않음 → Supabase 공개 API(anon 키)로는 못 읽음.
백엔드는 DB 소유자 계정으로 직접 연결하므로 영향 없음.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("patients", "auth_sessions", "consents")


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(30)),
        sa.Column("preferred_lang", sa.String(8), nullable=False, server_default="en"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Seoul"),
        sa.Column("age14_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "preferred_lang IN ('ko', 'en', 'zh-TW', 'zh-CN', 'vi')", name="ck_patients_lang"
        ),
    )
    op.create_index(
        "uq_patients_email_live",
        "patients",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Uuid(),
            sa.ForeignKey("patients.id", ondelete="CASCADE", name="fk_auth_sessions_patient_id_patients"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_auth_sessions_patient", "auth_sessions", ["patient_id"])
    op.create_index("ix_auth_sessions_expires", "auth_sessions", ["expires_at"])

    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Uuid(),
            sa.ForeignKey("patients.id", ondelete="SET NULL", name="fk_consents_patient_id_patients"),
        ),
        sa.Column("booking_request_id", sa.Uuid()),  # booking_requests(B) 생기면 FK 추가
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("lang", sa.String(8), nullable=False),
        sa.Column("agreed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "kind IN ('terms', 'privacy', 'health', 'overseas_transfer')", name="ck_consents_kind"
        ),
    )
    op.create_index("ix_consents_patient", "consents", ["patient_id"])

    if op.get_bind().dialect.name == "postgresql":
        for t in TABLES:
            op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("consents")
    op.drop_table("auth_sessions")
    op.drop_index("uq_patients_email_live", table_name="patients")
    op.drop_table("patients")
