"""FastAPI 앱 진입점. 실행: uv run fastapi dev backend/src/main.py

모듈 라우터는 여기서 include_router로 붙인다 (경로 앞 /api/v1).
"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from core.config import get_settings
from core.errors import register_error_handlers
from modules.auth.router import router as auth_router
from modules.fx.router import router as fx_router
from modules.patient.router import router as patient_router

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
    return {"status": "ok"}


api.include_router(auth_router)
api.include_router(patient_router)
api.include_router(fx_router)

app.include_router(api)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """첫 화면 → API 문서 (Swagger)."""
    return RedirectResponse("/docs")
