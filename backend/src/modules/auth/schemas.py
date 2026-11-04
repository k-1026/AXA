from pydantic import BaseModel, EmailStr, Field, field_validator

from modules.consent.schemas import ConsentIn
from modules.patient.schemas import Lang, Timezone

# 비밀번호 길이 규칙 (초안, 팀 확인). 최대 길이는 해시 계산 남용 방지
PASSWORD_MIN = 8
PASSWORD_MAX = 128


class SignupRequest(BaseModel):
    """회원가입. 로그인 전 브라우저에서 고른 언어·시간대를 같이 보냄."""

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    display_name: str | None = Field(default=None, max_length=30)  # 인사말 (실명 아니어도 됨)
    age14_confirmed: bool  # 만 14세 이상 (개인정보보호법 제22조의2)
    preferred_lang: Lang = "en"
    timezone: Timezone = "Asia/Seoul"
    consents: list[ConsentIn] = Field(default_factory=list, max_length=4)  # terms·privacy 필수

    @field_validator("display_name")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
