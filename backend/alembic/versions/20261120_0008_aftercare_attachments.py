"""사후관리 메시지 첨부 (aftercare_messages.attachments)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-20

- [{path, kind(image/video), name}] — 파일 자체는 Supabase Storage 비공개 버킷 `aftercare-media` (modules/media)
- 기존 행은 빈 목록. has_photo는 그대로 둠 (첨부가 있으면 true)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("aftercare_messages") as batch:
        batch.add_column(sa.Column("attachments", JSONT, nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    with op.batch_alter_table("aftercare_messages") as batch:
        batch.drop_column("attachments")
