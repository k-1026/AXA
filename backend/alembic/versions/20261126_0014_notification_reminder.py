"""알림 종류에 reminder 추가 (방문 전 리마인드)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-26

- docs/booking-rules.md 3-2 N1: 확정 예약 48시간·24시간·2시간 전 알림. 단계는 status 칸에 (48h·24h·2h)
- 보낸 기록이 곧 이 행 → 같은 단계를 두 번 보내지 않음 (별도 표 없음)
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as b:
        b.drop_constraint("ck_notifications_kind", type_="check")
        b.create_check_constraint("ck_notifications_kind", "kind IN ('status', 'reply', 'aftercare', 'reminder')")


def downgrade() -> None:
    op.execute("DELETE FROM notifications WHERE kind = 'reminder'")
    with op.batch_alter_table("notifications") as b:
        b.drop_constraint("ck_notifications_kind", type_="check")
        b.create_check_constraint("ck_notifications_kind", "kind IN ('status', 'reply', 'aftercare')")
