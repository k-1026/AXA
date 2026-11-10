"""챗봇 대화 저장 (chat_sessions, chat_messages) — 결정 2·5, 최소 저장

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-10

- 마이그레이션은 A가 만든다 (backend/AGENTS.md 4절, 결정 13)
- chat_sessions.state(jsonb): 체류 형태·요청서 초안·방금 보여 준 병원. docs/backend-db-schema.md 5절의 설계에 state를 더함
- chat_messages.sources는 쓰지 않아 뺐다 (공공 문서 검색 RAG를 붙일 때 추가)
- 환자 탈퇴 시 FK CASCADE로도 지워지지만, 백엔드는 DB에 기대지 않고 직접 지운다 (auth.service.withdraw)
Supabase: 테이블마다 RLS를 켜고 정책은 만들지 않음 (0001과 같음)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("chat_sessions", "chat_messages")


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Uuid(),
            sa.ForeignKey("patients.id", ondelete="CASCADE", name="fk_chat_sessions_patient_id_patients"),
            nullable=False,
        ),
        sa.Column("lang", sa.String(8), nullable=False),
        sa.Column("title", sa.String(60), nullable=False),
        sa.Column(
            "state",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("lang IN ('ko', 'en', 'zh-TW', 'zh-CN', 'vi')", name="ck_chat_sessions_lang"),
    )
    op.create_index("ix_chat_sessions_patient", "chat_sessions", ["patient_id", "last_message_at"])
    op.create_index("ix_chat_sessions_last_message", "chat_sessions", ["last_message_at"])

    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE", name="fk_chat_messages_session_id_chat_sessions"),
            nullable=False,
        ),
        sa.Column("role", sa.String(9), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("refused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
    )
    op.create_index("ix_chat_messages_session", "chat_messages", ["session_id", "id"])

    if op.get_bind().dialect.name == "postgresql":
        for t in TABLES:
            op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
