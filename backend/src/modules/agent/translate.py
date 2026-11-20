"""메시지 번역 (B 모듈 agent, A 작성 · B 확인, 결정 25). LLM 호출은 `ai/llm/client.py`만 (AGENTS.md 6절).

- 환자 글 → 한국어 (병원 직원용), 직원 글(한국어) → 환자 언어
- 요청서에 `overseas_transfer`(해외 LLM 번역) 동의가 있을 때만 → 없으면 원문만 (부르는 쪽이 `allowed()`로 확인)
- 보내기 전 개인정보 가림(`mask_pii`: 이메일·전화·여권·등록번호) → 번역문에도 [email] 같은 표시로 남음
- 실패·제공자 없음이면 None → 화면은 원문을 보여 줌 (번역 때문에 보내기가 실패하지 않음)
- 의료 판단을 덧붙이지 않도록 "번역만" 지시. 번역문은 참고용이고 원문이 기준
"""

from __future__ import annotations

import logging
import uuid
from functools import lru_cache

from sqlalchemy.orm import Session

from ai.llm.client import LLMClient
from ai.llm.safety import mask_pii
from modules.consent import service as consent_service

log = logging.getLogger(__name__)

LANG_NAMES = {
    "ko": "Korean", "en": "English", "vi": "Vietnamese",
    "zh-TW": "Traditional Chinese (Taiwan)", "zh-CN": "Simplified Chinese",
}
MAX_CHARS = 4000

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
    try:
        res = llm.chat(
            [{"role": "system", "content": SYSTEM.format(lang=LANG_NAMES[target])}, {"role": "user", "content": masked}],
            service="translate", tenant_id=str(tenant_id) if tenant_id else None, temperature=0,
        )
    except Exception as e:  # noqa: BLE001 — 번역 실패로 보내기가 실패하지 않게
        log.warning("번역 실패: %s", type(e).__name__)
        return None
    out = (res.text or "").strip()
    return out[:MAX_CHARS] or None


def for_request(db: Session, request_id: uuid.UUID, text: str | None, target: str, tenant_id: uuid.UUID | None = None) -> str | None:
    """동의 확인 + 같은 언어면 건너뜀 + 번역."""
    if target == "ko" and _is_korean(text) or not allowed(db, request_id):
        return None
    return translate(text, target, tenant_id=tenant_id)


def _is_korean(text: str | None) -> bool:
    letters = [c for c in text or "" if c.isalpha()]
    return bool(letters) and sum("가" <= c <= "힣" for c in letters) / len(letters) > 0.5
