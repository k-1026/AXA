"""웹 푸시 (A, 결정 30). 사이트 안 알림(notify)이 저장될 때 그 환자가 구독한 브라우저에 푸시.

- 내용: 종류·상태 코드·요청서 id·언어만 (글·건강정보·병원 이름 X). 문장은 브라우저의 서비스 워커가 언어별로 만듦
- 언제: 알림과 같은 처리가 **commit된 뒤** (`after_commit`) → 상태 변경이 취소되면 푸시도 안 감
- 푸시 서비스가 404·410(구독 끝남)을 주면 그 구독을 지움. 그 밖의 실패는 무시 (사이트 안 알림은 이미 저장됨)
- VAPID 키가 없으면 전부 끔 (`enabled() = False`, 키 API는 503 `push.unavailable`)
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import AppError
from modules.notification.models import PushSubscription
from modules.patient.models import Patient

log = logging.getLogger(__name__)
TTL_SECONDS = 24 * 3600  # 기기가 꺼져 있으면 하루까지 기다렸다 전달
TIMEOUT = 5
_PENDING = "pending_web_push"


def enabled() -> bool:
    s = get_settings()
    return bool(s.vapid_public_key and s.vapid_private_key)


def public_key() -> str:
    if not enabled():
        raise AppError(503, "push.unavailable", "웹 푸시를 쓸 수 없습니다")
    return get_settings().vapid_public_key


def subscribe(db: Session, patient_id: uuid.UUID, endpoint: str, p256dh: str, auth: str) -> None:
    """같은 브라우저(endpoint)면 키·환자를 새 값으로 (같은 기기에서 다른 계정으로 로그인한 경우 포함)."""
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    if sub is None:
        db.add(PushSubscription(patient_id=patient_id, endpoint=endpoint, p256dh=p256dh, auth=auth))
    else:
        sub.patient_id, sub.p256dh, sub.auth = patient_id, p256dh, auth
    db.commit()


def unsubscribe(db: Session, patient_id: uuid.UUID, endpoint: str) -> None:
    """내 구독만 지움 (남의 endpoint는 조용히 무시)."""
    db.execute(delete(PushSubscription).where(PushSubscription.patient_id == patient_id,
                                              PushSubscription.endpoint == endpoint))
    db.commit()


def queue(db: Session, patient_id: uuid.UUID, kind: str, request_id: uuid.UUID, status: str | None) -> None:
    """notify()가 부름 (commit 전). 구독을 지금 읽어 두고 commit 뒤에 보냄."""
    if not enabled():
        return
    subs = db.execute(select(PushSubscription.endpoint, PushSubscription.p256dh, PushSubscription.auth)
                      .where(PushSubscription.patient_id == patient_id)).all()
    if not subs:
        return
    lang = db.scalar(select(Patient.preferred_lang).where(Patient.id == patient_id)) or "en"
    payload = json.dumps({"kind": kind, "status": status, "request_id": str(request_id), "lang": lang})
    pending = db.info.setdefault(_PENDING, [])
    if not pending:  # 이 처리에서 처음이면 commit 뒤 한 번 보내도록 걸어 둠 (rollback이면 버림)
        event.listen(db, "after_commit", _flush, once=True)
        event.listen(db, "after_rollback", _drop, once=True)
    pending += [(tuple(s), payload) for s in subs]


def _drop(db: Session) -> None:
    db.info.pop(_PENDING, None)
    if event.contains(db, "after_commit", _flush):
        event.remove(db, "after_commit", _flush)


def _flush(db: Session) -> None:
    pending = db.info.pop(_PENDING, [])
    if event.contains(db, "after_rollback", _drop):
        event.remove(db, "after_rollback", _drop)
    gone = [endpoint for (endpoint, p256dh, auth), payload in pending if send(endpoint, p256dh, auth, payload) == "gone"]
    if gone:  # commit 뒤라 이 세션으로는 SQL을 못 씀 → 새 세션
        with Session(bind=db.get_bind()) as s:
            s.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(gone)))
            s.commit()


def send(endpoint: str, p256dh: str, auth: str, payload: str) -> str:
    """→ "ok" | "gone"(구독 끝남, 지움) | "failed". 테스트는 이 함수를 바꿔 끼움."""
    from pywebpush import WebPushException, webpush  # 무거운 의존성은 보낼 때만

    s = get_settings()
    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=payload, vapid_private_key=s.vapid_private_key, vapid_claims={"sub": s.vapid_subject},
            ttl=TTL_SECONDS, timeout=TIMEOUT,
        )
        return "ok"
    except WebPushException as e:
        code = getattr(e.response, "status_code", None)
        if code in (404, 410):
            return "gone"
        log.warning("web push failed: %s", code)
        return "failed"
    except Exception as e:  # noqa: BLE001 — 푸시 실패로 상태 변경 응답이 실패하지 않게
        log.warning("web push failed: %s", type(e).__name__)
        return "failed"
