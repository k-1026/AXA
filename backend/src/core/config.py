"""환경변수 설정. 값은 루트 .env에서 읽는다 (.env.example 참고)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # JWT — 비밀 키는 `openssl rand -hex 32` 등으로 만든 값을 .env에만 둔다
    # HS256 키는 32바이트 이상 권장 (RFC 7518 3.2절) → 짧으면 서버 시작 실패
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_patient_expire_minutes: int = 60 * 24
    jwt_staff_expire_minutes: int = 60 * 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
