"""환경변수 설정. 값은 루트 .env에서 읽는다 (.env.example 참고)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 어느 폴더에서 실행해도 루트 .env를 읽도록 파일 위치 기준 (backend/src/core/config.py → 루트)
ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")

    # JWT — 비밀 키는 `openssl rand -hex 32` 등으로 만든 값을 .env에만 둔다
    # HS256 키는 32바이트 이상 권장 (RFC 7518 3.2절) → 짧으면 서버 시작 실패
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_patient_expire_minutes: int = 60 * 24
    jwt_staff_expire_minutes: int = 60 * 8

    # DB — Supabase 연결 문자열 (postgresql+psycopg://...). 없으면 DB를 쓰는 API가 실패
    database_url: str | None = None

    # 프론트 주소 (CORS). 배포 시 .env에 CORS_ORIGINS=["https://…vercel.app"] 처럼 JSON 목록
    cors_origins: list[str] = ["http://localhost:5403", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
