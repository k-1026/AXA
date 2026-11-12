"""alembic_version 테이블도 RLS 켬 (Supabase 공개 API로 못 읽게)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04

Alembic이 직접 만드는 표라 0001에서 못 켰음. 백엔드·Alembic은 DB 소유자로 접속해 영향 없음.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY")
