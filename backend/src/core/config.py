"""환경변수 설정. 값은 루트 .env에서 읽는다 (.env.example 참고)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# JWT 알고리즘은 고정 (환경변수로 바꾸지 않음 → 알고리즘 혼동·none 공격 여지 없앰)
JWT_ALGORITHM = "HS256"

# 어느 폴더에서 실행해도 루트 .env를 읽도록 파일 위치 기준 (backend/src/core/config.py → 루트)
ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")

    # JWT — 비밀 키는 `openssl rand -hex 32` 등으로 만든 값을 .env에만 둔다
    # HS256 키는 32바이트 이상 권장 (RFC 7518 3.2절) → 짧으면 서버 시작 실패
    jwt_secret: str = Field(min_length=32)
    jwt_patient_expire_minutes: int = 60 * 24
    jwt_staff_expire_minutes: int = 60 * 8

    # DB — Supabase 연결 문자열 (postgresql+psycopg://...). 없으면 DB를 쓰는 API가 실패
    database_url: str | None = None

    # 환율: 한국은행 ECOS Open API 인증키 (ecos.bok.or.kr 에서 발급, .env에만)
    ecos_api_key: str | None = None
    fx_switch_hour_kst: int = 10  # 매일 이 시각(한국 시간)에 그날 적용 환율로 바뀜

    # 정기 정리 API(/internal/purge)용 비밀 값. 없으면 그 API는 꺼짐(404). Vercel Cron이 Bearer로 보냄
    cron_secret: str | None = Field(default=None, min_length=16)

    @field_validator("cron_secret", mode="before")
    @classmethod
    def _empty_is_none(cls, v: str | None) -> str | None:
        return v or None  # .env의 `CRON_SECRET=`(빈 값) = 없음

    # Supabase Storage (사후관리 사진·영상, 비공개 버킷). 둘 중 하나라도 없으면 업로드 API는 503 storage.unavailable
    # 서비스 키는 서버 전용 — 프론트·커밋에 넣지 않음 (Supabase 대시보드 → Project Settings → API)
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    # Realtime 알림 토큰 서명 (Supabase JWT Keys > Legacy JWT Secret, 결정 27). 없으면 알림은 주기 확인만
    supabase_jwt_secret: str | None = None
    # 웹 푸시 (결정 30). VAPID 키 한 쌍(base64url, `backend/scripts/make_vapid_keys.py`로 만듦). 없으면 푸시 끔
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:noreply@example.com"  # 푸시 서비스가 문제 있을 때 연락할 주소 (운영 때 팀 주소로)

    @field_validator("supabase_url", "supabase_service_role_key", "supabase_jwt_secret", "vapid_public_key",
                     "vapid_private_key", mode="before")
    @classmethod
    def _empty_str_is_none(cls, v: str | None) -> str | None:
        return v or None

    # 실제 병원(시드 가상 병원 is_demo가 아닌 곳) 입점 신청. 기본 끔 — 등록번호 확인·운영자 승인 절차가 생기기 전까지
    # (11/25: 확인 없이 남의 병원 주인으로 가입해 그 병원 환자 요청서를 받을 수 있었음). 로컬 개발에서만 .env로 켬
    staff_signup_real_hospitals: bool = False

    # 프론트 주소 (CORS). 배포 시 .env에 CORS_ORIGINS=["https://…vercel.app"] 처럼 JSON 목록
    cors_origins: list[str] = ["http://localhost:5403", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
