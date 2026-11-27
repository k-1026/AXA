"""내부 정리 API. 사람·프론트가 아니라 예약 작업만 부름 (문서에 숨김).

- 인증: `Authorization: Bearer <CRON_SECRET>` (Vercel Cron은 CRON_SECRET 환경변수가 있으면 이 헤더를 자동으로 붙임)
- CRON_SECRET이 없으면 꺼짐 → 404
- Vercel Cron은 GET으로 부르므로 GET·POST 둘 다 받음
"""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from core.config import get_settings
from core.db import get_db
from core.errors import AppError
from modules.maintenance import service
from modules.agent import translate
from modules.notification import reminders

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


def require_cron_secret(authorization: Annotated[str | None, Header()] = None) -> None:
    secret = get_settings().cron_secret
    if not secret:
        raise AppError(404, "not_found", "Not Found")
    scheme, _, value = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(value.encode(), secret.encode()):
        raise AppError(401, "auth.required", "인증이 필요합니다")


@router.api_route("/purge", methods=["GET", "POST"], dependencies=[Depends(require_cron_secret)])
def purge(db: Annotated[Session, Depends(get_db)]) -> dict[str, int]:
    """30일 지난 대화·죽은 로그인 세션·DB에 없는 사진·영상 파일 삭제 → 지운 수."""
    return service.purge(db)


@router.api_route("/reminders", methods=["GET", "POST"], dependencies=[Depends(require_cron_secret)])
def send_reminders(db: Annotated[Session, Depends(get_db)]) -> dict[str, int]:
    """확정 예약 방문 48·24·2시간 전 알림 → 보낸 수. 1시간마다 불러야 함 (.github/workflows/reminders.yml)."""
    return {"reminders": reminders.send_due(db)}


@router.api_route("/translations", methods=["GET", "POST"], dependencies=[Depends(require_cron_secret)])
def retry_translations(db: Annotated[Session, Depends(get_db)]) -> dict[str, int]:
    """번역이 실패해 빠진 글을 모든 병원에서 다시 번역 (최대 50개). 1시간마다 (.github/workflows/reminders.yml, 11/27)."""
    return translate.retry_missing(db, None, limit=50)
