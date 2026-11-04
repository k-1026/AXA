"""에러 형식 통일: {code, message, detail}. code는 docs/backend-contracts.md 4절 목록만 쓴다."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str = "", detail: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message or code
        self.detail = detail if detail is not None else {}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
            headers=headers,
        )

    # FastAPI 기본 422({"detail": [...]})도 같은 형식으로 → 프론트는 code만 보면 됨
    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": e.get("loc"), "type": e.get("type"), "msg": e.get("msg")} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation",
                "message": "입력 값을 확인하세요",
                "detail": {"errors": jsonable_encoder(errors)},
            },
        )
