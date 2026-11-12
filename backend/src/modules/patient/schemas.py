import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Annotated

Lang = Literal["ko", "en", "zh-TW", "zh-CN", "vi"]


def _check_tz(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("IANA 시간대 이름이 아닙니다 (예: Asia/Taipei)")
    return value


Timezone = Annotated[str, Field(max_length=64), AfterValidator(_check_tz)]


def blank_to_none(v: str | None) -> str | None:
    """인사말 이름: 앞뒤 공백 제거, 비면 None (가입·PATCH /me 공용)."""
    return (v.strip() or None) if v is not None else None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    preferred_lang: Lang
    timezone: str
    created_at: datetime


class PatientUpdate(BaseModel):
    """PATCH /me — 보낸 칸만 바꿈. display_name을 null로 보내면 지움(인사말은 이메일 앞부분)."""

    display_name: str | None = Field(default=None, max_length=30)
    preferred_lang: Lang | None = None
    timezone: Timezone | None = None

    @field_validator("display_name")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return blank_to_none(v)
