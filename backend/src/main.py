"""FastAPI 앱 진입점. 실행: uv run fastapi dev backend/src/main.py

모듈 라우터는 여기서 include_router로 붙인다 (경로 앞 /api/v1).
"""

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from core import db as core_db
from core.config import get_settings
from core.errors import AppError, register_error_handlers
from modules.auth.router import router as auth_router
from modules.chatbot.router import router as chatbot_router
from modules.fx.router import router as fx_router
from modules.maintenance.router import router as maintenance_router
from modules.patient.router import router as patient_router

log = logging.getLogger(__name__)

app = FastAPI(title="AXA API", version="0.1.0")
register_error_handlers(app)
# 토큰은 Authorization 헤더로만 (쿠키 X) → credentials 끔
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

api = APIRouter(prefix="/api/v1")


@api.get("/health")
def health() -> dict[str, str]:
    """서버 + DB 연결 확인. DB에 연결할 수 없으면 503 `db.unavailable`."""
    try:
        with core_db.get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — DATABASE_URL 없음(RuntimeError)·연결 실패(SQLAlchemyError) 모두
        # 연결 문자열(비밀번호)이 메시지에 들어갈 수 있어 로그에는 예외 종류만
        log.error("health: DB 연결 실패 (%s)", type(exc).__name__)
        raise AppError(503, "db.unavailable", "DB에 연결할 수 없습니다") from None
    return {"status": "ok", "db": "ok"}


api.include_router(auth_router)
api.include_router(patient_router)
api.include_router(fx_router)
api.include_router(chatbot_router)
api.include_router(maintenance_router)

app.include_router(api)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """첫 화면 → API 문서 (Swagger)."""
    return RedirectResponse("/docs")
