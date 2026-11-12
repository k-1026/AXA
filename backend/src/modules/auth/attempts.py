"""로그인 시도 제한 (계약 4절 `auth.too_many_attempts` 429).

- 이메일당 15분에 5번 실패하면 막음 (탈퇴 비밀번호 확인도 같은 이메일 기록을 씀)
- 같은 IP에서 15분에 20번 실패하면 막음 (여러 이메일을 돌려 가며 맞추는 것 방지)
- 로그인 성공하면 그 이메일 기록만 지움 (IP 기록은 시간이 지나야 풀림)
- 없는 이메일도 똑같이 막음 → 응답으로 가입 여부를 알 수 없음

운영에서는 공유 저장소로 교체: 지금은 프로세스 메모리라 서버리스·여러 인스턴스에서는 인스턴스마다 따로 센다.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

from core.errors import AppError

MAX_KEYS = 10_000  # 키(이메일·IP)가 이보다 많아지면 끝난 기록을 정리


class AttemptLimiter:
    def __init__(self, max_failures: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.max_failures = max_failures
        self.window = window_seconds
        self.clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = {}

    def _prune(self, key: str, now: float) -> deque[float] | None:
        q = self._failures.get(key)
        if q is None:
            return None
        while q and q[0] <= now - self.window:
            q.popleft()
        if not q:
            del self._failures[key]
            return None
        return q

    def retry_after(self, key: str) -> int | None:
        """막혀 있으면 풀릴 때까지 초, 아니면 None."""
        with self._lock:
            now = self.clock()
            q = self._prune(key, now)
            if q is None or len(q) < self.max_failures:
                return None
            return max(1, math.ceil(q[-self.max_failures] + self.window - now))

    def fail(self, key: str) -> None:
        with self._lock:
            now = self.clock()
            if len(self._failures) >= MAX_KEYS:
                for k in list(self._failures):
                    self._prune(k, now)
            self._failures.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


by_email = AttemptLimiter(max_failures=5, window_seconds=15 * 60)
by_ip = AttemptLimiter(max_failures=20, window_seconds=15 * 60)


def client_ip(request: Request) -> str | None:
    """시도 제한용 IP. X-Forwarded-For는 위조할 수 있어 보지 않음 (배포 환경의 프록시 IP 전달 방식은 팀 확인)."""
    return request.client.host if request.client else None


def check(email: str, ip: str | None) -> None:
    """막혀 있으면 429. email은 정규화한 값."""
    waits = [by_email.retry_after(email)]
    if ip:
        waits.append(by_ip.retry_after(ip))
    wait = max((w for w in waits if w is not None), default=None)
    if wait is not None:
        raise AppError(
            429, "auth.too_many_attempts", "시도가 너무 많습니다. 잠시 뒤 다시 시도하세요", {"retry_after": wait}
        )


def failed(email: str, ip: str | None) -> None:
    by_email.fail(email)
    if ip:
        by_ip.fail(ip)


def succeeded(email: str) -> None:
    by_email.reset(email)


def reset_all() -> None:
    """테스트용."""
    by_email.clear()
    by_ip.clear()
