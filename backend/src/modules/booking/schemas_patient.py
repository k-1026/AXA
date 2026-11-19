"""환자 쪽 예약 요청 입력·응답 (A). docs/backend-contracts.md 6절 `BookingCreate`."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from modules.booking.models import CANCEL_REASONS
from modules.booking.schemas import BookingOut
from modules.consent.schemas import ConsentIn

Lang = Literal["ko", "en", "zh-TW", "zh-CN", "vi"]


class BookingCreate(BaseModel):
    """환자가 고른 병원 1곳에 보내는 예약 요청. 확정은 병원 직원만 (상태는 항상 pending으로 시작)."""

    department_code: str = Field(min_length=1, max_length=30)
    preferred_slots: list[datetime] = Field(min_length=1, max_length=3)  # 희망 일시 (시간대 포함, UTC로 저장)
    patient_timezone: str = Field(min_length=1, max_length=64)  # IANA (예 Asia/Taipei), 화면 표시용
    lang: Lang
    nationality: str = Field(pattern=r"^[A-Z]{2}$")  # ISO 3166-1 alpha-2
    contact_method: str = Field(min_length=1, max_length=20)
    visa_needed: bool = False
    treatment: str | None = Field(default=None, max_length=60)
    message: str | None = Field(default=None, max_length=2000)  # 자유 입력 원문 (번역은 나중에)
    health_info: str | None = Field(default=None, max_length=2000)  # 있으면 health 동의 필수
    # 체류 형태: 국내 거주 외국인은 유치 대상이 아님 (의료법 제27조 제3항 제2호) → short_term만 받음
    residency: Literal["short_term"]
    consents: list[ConsentIn] = Field(default_factory=list, max_length=4)

    @field_validator("preferred_slots")
    @classmethod
    def _future_aware(cls, v: list[datetime]) -> list[datetime]:
        now = datetime.now(timezone.utc)
        for s in v:
            if s.tzinfo is None:
                raise ValueError("희망 일시에 시간대가 필요합니다")
            if s <= now:
                raise ValueError("희망 일시는 지금 이후여야 합니다")
        return [s.astimezone(timezone.utc) for s in v]


class CancelIn(BaseModel):
    reason: Literal[CANCEL_REASONS] | None = None  # type: ignore[valid-type]


class ReplyOut(BaseModel):
    """직원이 승인해 보낸 답장만 (sent_at 있음). 초안·AI 초안 표시는 환자에게 안 보임."""

    text_ko: str
    text_translated: str | None
    sent_at: datetime


class PatientBookingOut(BookingOut):
    replies: list[ReplyOut] = []
