from pydantic import BaseModel, EmailStr, Field, field_validator

from modules.consent.schemas import ConsentIn
from modules.patient.schemas import Lang, ResidencyIn, Timezone, blank_to_none

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
    # 거주국 + 3문항 (결정 28). 없으면 비워 두고 첫 예약 요청 전에 PUT /me/residency로 받음
    residency: ResidencyIn | None = None

    @field_validator("display_name")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return blank_to_none(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class WithdrawRequest(BaseModel):
    """탈퇴 확인용 비밀번호 (토큰만 있으면 남이 대신 탈퇴시키지 못하게)."""

    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StaffSignupRequest(BaseModel):
    """입점 병원 가입 (병원 관계자). 등록 외국인환자 유치의료기관만 → 병원 계정(tenant) + 대표 직원(owner).

    프로토타입: 등록번호는 형식만 확인하고 바로 사용. 실서비스는 운영자가 사업자·등록증을 확인한 뒤 활성화 (팀 확인)
    """

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    hospital_id: int
    registration_no: str = Field(pattern=r"^M-\d{4}-\d{2}-\d{2}-\d{4,6}$")  # 외국인환자 유치의료기관 등록번호
    consents: list[ConsentIn] = Field(default_factory=list, max_length=4)  # terms·privacy 필수


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)
