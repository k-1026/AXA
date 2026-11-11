"""재시도와 속도 제한(429) 처리.

오류 분류 → client.py가 다음 행동을 정한다.
- RateLimitError (429, 한도 소진)   : 같은 제공자 재시도 X, 바로 다음 제공자로
- TransientError (5xx, 타임아웃, 연결) : 같은 제공자에서 지수 백오프로 재시도, 그래도 실패면 다음 제공자로
- RequestError   (그 밖의 4xx)       : 요청 자체가 잘못됨 → 다른 제공자로 넘기지 않고 바로 실패
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

import httpx

T = TypeVar("T")


class LLMError(Exception):
    def __init__(self, message: str, provider: str = "", status: int | None = None):
        super().__init__(message)
        self.provider = provider
        self.status = status


class RateLimitError(LLMError):
    pass


class TransientError(LLMError):
    pass


class RequestError(LLMError):
    pass


class AllProvidersFailed(LLMError):
    def __init__(self, errors: list[LLMError]):
        detail = "; ".join(f"{e.provider}: {e}" for e in errors) or "사용 가능한 제공자 없음 (.env의 API 키 확인)"
        super().__init__(f"모든 LLM 제공자 실패: {detail}")
        self.errors = errors


def classify_http_error(provider: str, response: httpx.Response) -> LLMError:
    status = response.status_code
    body = response.text[:300]
    if status == 429:
        return RateLimitError(f"한도 초과 (429): {body}", provider, status)
    if status >= 500:
        return TransientError(f"서버 오류 ({status}): {body}", provider, status)
    return RequestError(f"요청 오류 ({status}): {body}", provider, status)


def with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int,
    base_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """TransientError만 재시도. 나머지 오류는 그대로 올린다."""
    attempt = 0
    while True:
        try:
            return fn()
        except TransientError:
            if attempt >= max_retries:
                raise
            sleep(base_delay * (2**attempt))
            attempt += 1
