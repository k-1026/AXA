"""호출마다 토큰·비용을 서비스·병원(tenant)별로 기록한다.

지금은 메모리 + (설정 시) JSONL 파일. DB 테이블(`llm_usage`)이 생기면 record()만 바꾼다.
기록에는 프롬프트 내용을 넣지 않는다 (개인정보 X).
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class UsageRecord:
    service: str  # "chatbot" | "agent" | ...
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    ok: bool
    tenant_id: str | None = None
    fallback_from: str | None = None  # 앞 제공자가 실패해 넘어온 경우 그 이름
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UsageTracker:
    def __init__(self, log_path: str = ""):
        self._records: list[UsageRecord] = []
        self._lock = threading.Lock()
        self._path = Path(log_path) if log_path else None

    def record(self, rec: UsageRecord) -> None:
        with self._lock:
            self._records.append(rec)
            if self._path:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    @property
    def records(self) -> list[UsageRecord]:
        with self._lock:
            return list(self._records)

    def totals(self) -> dict[str, dict[str, int]]:
        """제공자별 호출 수·토큰 합계."""
        out: dict[str, dict[str, int]] = {}
        for r in self.records:
            t = out.setdefault(r.provider, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
            t["calls"] += 1
            t["prompt_tokens"] += r.prompt_tokens
            t["completion_tokens"] += r.completion_tokens
        return out
