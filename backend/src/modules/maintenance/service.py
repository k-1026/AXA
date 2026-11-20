"""정기 정리 (보관 기간): 30일 지난 챗봇 대화 + 만료·로그아웃한 로그인 세션 + DB에 없는 사진·영상 파일 삭제.

POST(·GET) /api/v1/internal/purge가 부른다. 예약 작업(Vercel Cron 등)이 하루 1번 불러야 함 — 부르지 않으면 지워지지 않음.
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from ai.agent.service import RETENTION_DAYS
from core.db import utcnow
from modules.aftercare import service as aftercare_service
from modules.auth import sessions as auth_sessions
from modules.chatbot import sessions as chat_sessions
from modules.media import service as media

# 올리고 아직 보내지 않은 파일을 지우지 않게 (업로드 주소는 2시간 유효) 하루 지난 것만
MEDIA_GRACE = timedelta(days=1)


def purge(db: Session) -> dict[str, int]:
    """한 번에 commit. 지운 행 수 (대화 = 세션 수)."""
    chats = chat_sessions.purge_older_than(db, utcnow() - timedelta(days=RETENTION_DAYS))
    dead = auth_sessions.purge_dead(db)
    db.commit()
    return {"chat_sessions": chats, "auth_sessions": dead, "media_files": purge_media(db)}


def purge_media(db: Session) -> int:
    """Storage에는 있는데 어떤 메시지도 가리키지 않는 파일 (보내지 않은 업로드, 탈퇴 때 못 지운 것, 지워진 대화) → 삭제 수.
    저장소 설정이 없거나 Storage 오류면 0 (다른 정리는 그대로 끝남)."""
    if not media.enabled():
        return 0
    try:
        objects = media.list_objects()
    except Exception:  # noqa: BLE001 — Storage 문제로 DB 정리까지 실패하지 않게
        return 0
    used = aftercare_service.referenced_media_paths(db)
    cutoff = utcnow() - MEDIA_GRACE
    stale = [p for p, created in objects if p not in used and created is not None and created < cutoff]
    return media.remove(stale)
