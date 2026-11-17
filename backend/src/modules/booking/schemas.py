import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    """confirm·propose는 시간(slot, UTC)을 받음. 확정할 때 이미 제안한 시간이 있으면 생략 가능."""

    slot: datetime | None = None
