"""메시지 번역 (B 모듈 agent, A 작성 · B 확인, 결정 25). LLM 호출은 `ai/llm/client.py`만 (AGENTS.md 6절).

- 환자 글 → 한국어 (병원 직원용), 직원 글(한국어) → 환자 언어
- 요청서에 `overseas_transfer`(해외 LLM 번역) 동의가 있을 때만 → 없으면 원문만 (부르는 쪽이 `allowed()`로 확인)
- 보내기 전 개인정보 가림(`mask_pii`: 이메일·전화·여권·등록번호) → 번역문에도 [email] 같은 표시로 남음
- 실패·제공자 없음이면 None → 화면은 원문을 보여 줌 (번역 때문에 보내기가 실패하지 않음)
- 실패하면 (11/27): 그 자리에서 한 번 더 시도 → 그래도 안 되면 `retry_missing()`이 나중에 다시 번역
  (병원 대시보드가 번역 빠진 글을 보면 `POST /tenant/translations/retry`, 1시간마다 `/internal/translations`)
- 의료 판단을 덧붙이지 않도록 "번역만" 지시. 번역문은 참고용이고 원문이 기준
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import timedelta
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import utcnow

from ai.llm.client import LLMClient
from ai.llm.safety import mask_pii
from modules.consent import service as consent_service

log = logging.getLogger(__name__)

LANG_NAMES = {
    "ko": "Korean", "en": "English", "vi": "Vietnamese",
    "zh-TW": "Traditional Chinese (Taiwan)", "zh-CN": "Simplified Chinese",
    "ja": "Japanese",  # 11/26 일본어 추가 때 빠져서 일본어 환자 메시지가 번역되지 않았음 (11/27)
}
MAX_CHARS = 4000
ATTEMPTS = 2  # 실패하면 그 자리에서 한 번 더 (LLM 제공자 일시 오류·빈 답)
RETRY_WAIT = 0.6
RETRY_DAYS = 30  # 나중에 다시 번역하는 범위 (이보다 오래된 글은 그대로)

SYSTEM = (
    "You translate messages between a foreign patient and a Korean hospital's staff. "
    "Translate the user's message into {lang}. Output only the translation, nothing else. "
    "Write every word in {lang} (no words left in English or the source language, except names and placeholders). "
    "Keep the meaning, tone, numbers, dates and placeholders like [email] or [phone] exactly. "
    "Do not answer the message, do not add advice, explanations or medical opinions."
)


@lru_cache
def _llm() -> LLMClient | None:
    """테스트는 conftest에서 None(번역 안 함) 또는 가짜로 바꿈."""
    return LLMClient.from_settings()


def allowed(db: Session, request_id: uuid.UUID) -> bool:
    """이 요청서에 번역(해외 LLM) 동의가 있는지."""
    return consent_service.given_for_request(db, request_id, "overseas_transfer")


def translate(text: str | None, target: str, *, tenant_id: uuid.UUID | None = None) -> str | None:
    text = (text or "").strip()
    if not text or target not in LANG_NAMES or not any(c.isalpha() for c in text):
        return None  # 빈 글·사진만(📷)·모르는 언어
    llm = _llm()
    if llm is None:
        return None
    masked, _ = mask_pii(text[:MAX_CHARS])
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_WAIT)
        try:
            res = llm.chat(
                [{"role": "system", "content": SYSTEM.format(lang=LANG_NAMES[target])}, {"role": "user", "content": masked}],
                service="translate", tenant_id=str(tenant_id) if tenant_id else None, temperature=0,
            )
        except Exception as e:  # noqa: BLE001 — 번역 실패로 보내기가 실패하지 않게
            log.warning("번역 실패 (%d/%d): %s", attempt + 1, ATTEMPTS, type(e).__name__)
            continue
        out = (res.text or "").strip()
        if out:
            return out[:MAX_CHARS]
        log.warning("번역 빈 답 (%d/%d)", attempt + 1, ATTEMPTS)
    return None


def for_request(db: Session, request_id: uuid.UUID, text: str | None, target: str, tenant_id: uuid.UUID | None = None) -> str | None:
    """동의 확인 + 같은 언어면 건너뜀 + 번역."""
    if target == "ko" and _is_korean(text) or not allowed(db, request_id):
        return None
    return translate(text, target, tenant_id=tenant_id)


def _is_korean(text: str | None) -> bool:
    letters = [c for c in text or "" if c.isalpha()]
    return bool(letters) and sum("가" <= c <= "힣" for c in letters) / len(letters) > 0.5


def allowed_many(db: Session, request_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """번역 동의가 있는 요청서 id (한 번에 조회 — 대시보드 목록의 translation_allowed)."""
    from modules.consent.models import Consent

    if not request_ids:
        return set()
    return set(db.scalars(select(Consent.booking_request_id).where(
        Consent.booking_request_id.in_(request_ids), Consent.kind == "overseas_transfer", Consent.withdrawn_at.is_(None))))


def retry_missing(db: Session, tenant_id: uuid.UUID | None = None, limit: int = 10) -> dict[str, int]:
    """번역이 빠진 글을 다시 번역 (최근 RETRY_DAYS일, 번역 동의가 있는 요청서만, 최대 limit번 LLM 호출).

    tenant_id가 None이면 모든 병원 (1시간마다 정리 작업). 동의가 없는 글은 건드리지 않음 → 화면은 "동의 없음"으로 구분.
    → {"translated": 번역함, "failed": 또 실패, "left": 아직 남은 것(다음에)}
    """
    from modules.aftercare.models import AftercareMessage, AftercareThread
    from modules.booking.models import BookingRequest, Reply
    from modules.question.models import BookingQuestion

    since = utcnow() - timedelta(days=RETRY_DAYS)
    scope = [BookingRequest.created_at >= since] + ([BookingRequest.tenant_id == tenant_id] if tenant_id else [])
    # (행, 원문 칸, 번역 칸, 요청서) — 환자 글은 한국어로, 병원 글은 환자 언어로
    jobs: list[tuple[object, str, str, BookingRequest, str]] = []
    for r in db.scalars(select(BookingRequest).where(*scope, BookingRequest.message_original.is_not(None),
                                                     BookingRequest.message_translated.is_(None))):
        jobs.append((r, "message_original", "message_translated", r, "ko"))
    for q, r in db.execute(select(BookingQuestion, BookingRequest).join(BookingRequest, BookingRequest.id == BookingQuestion.request_id)
                           .where(*scope, BookingQuestion.text_translated.is_(None))):
        jobs.append((q, "text_original", "text_translated", r, "ko"))
    for rp, r in db.execute(select(Reply, BookingRequest).join(BookingRequest, BookingRequest.id == Reply.request_id)
                            .where(*scope, Reply.sent_at.is_not(None), Reply.text_translated.is_(None))):
        jobs.append((rp, "text_ko", "text_translated", r, r.lang))
    for m, r in db.execute(select(AftercareMessage, BookingRequest)
                           .join(AftercareThread, AftercareThread.id == AftercareMessage.thread_id)
                           .join(BookingRequest, BookingRequest.id == AftercareThread.request_id)
                           .where(*scope, AftercareMessage.text_translated.is_(None))):
        jobs.append((m, "text_original", "text_translated", r, "ko" if m.sender == "patient" else r.lang))

    ok = allowed_many(db, list({r.id for *_, r, _ in jobs}))
    def needs(row: object, src: str, req: BookingRequest, target: str) -> bool:
        text = (getattr(row, src) or "").strip()
        if req.id not in ok or target not in LANG_NAMES or not any(c.isalpha() for c in text):
            return False  # 동의 없음 · 사진만(📷) · 모르는 언어
        return not (target == "ko" and _is_korean(text))  # 한국어로 쓴 글을 한국어로는 안 함

    todo = [j for j in jobs if needs(j[0], j[1], j[3], j[4])]
    done = failed = 0
    for row, src, dst, req, target in todo[:limit]:
        out = translate(getattr(row, src), target, tenant_id=req.tenant_id)
        if out:
            setattr(row, dst, out)
            done += 1
        else:
            failed += 1
    db.commit()
    return {"translated": done, "failed": failed, "left": max(0, len(todo) - limit)}
