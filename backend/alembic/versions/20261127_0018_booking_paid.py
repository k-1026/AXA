"""예약 상태에 결제 확인(paid) + 결제 금액·수단

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-27

- 흐름: 요청(pending) → 확정(confirmed) → 방문 완료(visited) → **결제 확인(paid)**. 병원이 실제 결제 금액(원, 부가세 제외)·수단을 넣으면 paid
- 요금안 v4: 수수료 = 방문 완료·결제 확인된 진료비 × 요율 → 대시보드 "진료·결제 확인" 탭이 이 값으로 계산 (전에는 예시)
- booking_requests.status·booking_events.to_status CHECK에 paid 추가, booking_requests에 paid_amount·paid_method
- 되돌릴 때 paid 행이 있으면 CHECK를 다시 만들 수 없다 → downgrade 전에 정리
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | Sequence[str] | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = ("pending", "proposed", "confirmed", "rejected", "cancelled", "expired", "visited", "no_show")
NEW = (*OLD, "paid")
PAY_METHODS = ("card", "cash", "transfer", "other")
TARGETS = (("booking_requests", "status", "ck_booking_requests_status"),
           ("booking_events", "to_status", "ck_booking_events_to_status"))


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def _swap(values: tuple[str, ...]) -> None:
    for table, col, name in TARGETS:
        with op.batch_alter_table(table) as b:
            b.drop_constraint(name, type_="check")
            b.create_check_constraint(name, _in(col, values))


def upgrade() -> None:
    _swap(NEW)
    with op.batch_alter_table("booking_requests") as b:
        b.add_column(sa.Column("paid_amount", sa.Integer()))
        b.add_column(sa.Column("paid_method", sa.String(12)))
        b.create_check_constraint("ck_booking_requests_paid_amount", "paid_amount IS NULL OR paid_amount > 0")
        b.create_check_constraint("ck_booking_requests_paid_method", "paid_method IS NULL OR " + _in("paid_method", PAY_METHODS))


def downgrade() -> None:
    with op.batch_alter_table("booking_requests") as b:
        b.drop_constraint("ck_booking_requests_paid_method", type_="check")
        b.drop_constraint("ck_booking_requests_paid_amount", type_="check")
        b.drop_column("paid_method")
        b.drop_column("paid_amount")
    _swap(OLD)
