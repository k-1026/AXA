import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingOut(BaseModel):
    """병원·환자 공통 요청서 응답. 값은 코드로 (문장은 프론트)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    hospital_id: int
    status: str
    lang: str
    nationality: str
    contact_method: str
    preferred_slots: list[str]
    department_code: str
    treatment: str | None
    visa_needed: bool
    message_original: str | None
    message_translated: str | None
    channel: str
    confirmed_slot: datetime | None
    created_at: datetime


class StaffAction(BaseModel):
    """confirm·propose는 시간(slot, UTC)을 받음. 확정할 때 이미 제안한 시간이 있으면 생략 가능.
    reject는 사유 코드(reason, 선택): fully_booked · not_offered · needs_consult · other (contracts 2절)"""

    slot: datetime | None = None
    reason: str | None = None


class ReplyIn(BaseModel):
    """병원 직원 상담 답장 (한국어). 확인 창에서 보내기 = 승인 → 바로 발송"""

    text: str = Field(min_length=1, max_length=2000)


class ReplyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text_ko: str
    text_translated: str | None  # 번역 연결 전이면 비어 있음
    sent_at: datetime


class TenantBookingOut(BookingOut):
    """병원용 응답: 요청서 + 보낸 답장 (대시보드 상담 채팅·안 읽음 표시용)"""

    replies: list[ReplyOut] = []
    # 방문 전 환자 질문 [{text_original, text_translated(한국어), created_at}] — A 추가 (결정 32, B 확인)
    questions: list[dict] = []
