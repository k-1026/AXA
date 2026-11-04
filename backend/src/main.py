"""FastAPI 앱 진입점. 실행: uv run fastapi dev backend/src/main.py

모듈 라우터는 여기서 include_router로 붙인다 (경로 앞 /api/v1).
"""

from fastapi import APIRouter, FastAPI

from core.errors import register_error_handlers

app = FastAPI(title="AXA API", version="0.1.0")
register_error_handlers(app)

api = APIRouter(prefix="/api/v1")


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api)
