"""언어 코드에 일본어(ja) 추가

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-26

- 프론트에 일본어 화면이 있는데 백엔드 언어 목록(ko·en·zh-TW·zh-CN·vi)에 없어서, 일본어 사용자는 선호 언어·상담 언어·챗봇 언어로
  일본어를 고를 수 없었음 (챗봇은 영어로 바꿔 보냄)
- 세 표의 언어 CHECK를 다시 만든다: patients.preferred_lang, booking_requests.lang, chat_sessions.lang
- 되돌릴 때 이미 ja로 저장된 행이 있으면 CHECK를 다시 만들 수 없다 → downgrade 전에 그 행을 정리해야 함
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = ("ko", "en", "zh-TW", "zh-CN", "vi")
NEW = (*OLD, "ja")
TARGETS = (("patients", "preferred_lang", "ck_patients_lang"),
           ("booking_requests", "lang", "ck_booking_requests_lang"),
           ("chat_sessions", "lang", "ck_chat_sessions_lang"))


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def _swap(values: tuple[str, ...]) -> None:
    for table, col, name in TARGETS:
        with op.batch_alter_table(table) as b:
            b.drop_constraint(name, type_="check")
            b.create_check_constraint(name, _in(col, values))


def upgrade() -> None:
    _swap(NEW)


def downgrade() -> None:
    _swap(OLD)
