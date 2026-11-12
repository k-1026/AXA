"""에러 형식 통일: {code, message, detail}. code는 docs/backend-contracts.md 4절 목록만 쓴다."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger(__name__)

# 경로·메서드가 없을 때 FastAPI가 내는 404·405. 리소스가 없다는 `not_found`와 일부러 다른 코드:
# 프론트는 `not_found`를 "서버에 이미 없음"으로 보고 화면에서 지우는 곳이 있음 (챗봇 대화 삭제 등)
# → 배포 버전이 어긋나 경로가 없을 때 데이터를 잘못 지우지 않게
_ROUTE_ERRORS = {
    404: ("api.not_found", "없는 API 경로입니다"),
    405: ("api.method_not_allowed", "이 경로에서 쓸 수 없는 메서드입니다"),
}


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str = "", detail: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message or code
        self.detail = detail if detail is not None else {}


class _CatchAll:
    """처리하지 못한 예외 → 500 `internal` (같은 형식). 로그에는 예외 종류만 (메시지에 개인정보가 있을 수 있음).

    `exception_handler(Exception)` 대신 미들웨어로: Starlette는 그 핸들러 뒤에 예외를 다시 던져
    서버가 메시지 포함 traceback을 로그에 남기고, 응답에 CORS 헤더도 붙지 않음.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def _send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:  # noqa: BLE001 — 마지막 안전망
            log.error("처리하지 못한 예외: %s", type(exc).__name__)
            if started:  # 응답을 이미 보내기 시작함 → 더 할 수 있는 것 없음
                return
            response = JSONResponse(
                status_code=500,
                content={"code": "internal", "message": "서버 오류가 발생했습니다", "detail": {}},
            )
            await response(scope, receive, send)


def register_error_handlers(app: FastAPI) -> None:
    # CORS보다 먼저 등록 → CORS 미들웨어 안쪽 (500 응답에도 CORS 헤더가 붙음)
    app.add_middleware(_CatchAll)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
            headers=headers,
        )

    # 없는 경로 404·없는 메서드 405도 같은 형식으로. 그 밖의 HTTPException은 지금 코드에서 쓰지 않음 → 기본 처리
    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code not in _ROUTE_ERRORS:
            return await http_exception_handler(request, exc)
        code, message = _ROUTE_ERRORS[exc.status_code]
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": message, "detail": {}},
            headers=getattr(exc, "headers", None),  # 405의 Allow 헤더 유지
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
