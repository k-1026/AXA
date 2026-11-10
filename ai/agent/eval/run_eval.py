"""평가 실행기.

    python -m ai.agent.eval.run_eval --safety                  # 안전 검사 (LLM 없음, 즉시)
    python -m ai.agent.eval.run_eval --intent --limit 8        # 실제 모델로 의도→도구 확인 (일부만)
    python -m ai.agent.eval.run_eval --intent --ids dept-en,price-en --sleep 8

- 결과는 ai/agent/eval/results/ 에 마크다운 표로 저장 (날짜-종류.md)
- --intent 는 모델을 부른다 → 가상 데이터만 사용. 무료 키는 하루 한도가 있으니 --limit 로 나눠 돌린다
- 한도(429)가 나면 해당 문장을 "한도"로 표시하고 계속하지 않고 멈춘다 (다음에 --skip 으로 이어서)
"""

from __future__ import annotations

import argparse
import time
from datetime import date
from pathlib import Path

from ai.agent.core.orchestrator import ConversationState, Orchestrator
from ai.agent.eval.cases import INTENT_CASES, SAFETY_CASES
from ai.agent.tools.chat_tools import build_registry
from ai.llm.client import LLMClient
from ai.llm.retry import AllProvidersFailed, LLMError
from ai.llm.safety import check

RESULTS = Path(__file__).parent / "results"


def run_safety() -> tuple[list[str], int, int]:
    rows, ok = [], 0
    for c in SAFETY_CASES:
        r = check(c.text, c.lang)
        good = r.action == c.action and set(c.categories) <= set(r.categories)
        ok += good
        rows.append(f"| {'O' if good else 'X'} | {c.lang} | {c.text[:60]} | {c.action} {list(c.categories)} | {r.action} {r.categories} | {c.note} |")
    head = ["| 결과 | 언어 | 문장 | 기대 | 실제 | 메모 |", "|---|---|---|---|---|---|"]
    return head + rows, ok, len(SAFETY_CASES)


def run_intent(args) -> tuple[list[str], int, int, str]:
    client = LLMClient.from_settings()
    orch = Orchestrator(client, build_registry(), safety_check=check)
    cases = INTENT_CASES
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c.id in wanted]
    cases = cases[args.skip:]
    if args.limit:
        cases = cases[: args.limit]

    rows, ok, done, stopped = [], 0, 0, ""
    for c in cases:
        state = ConversationState(language=c.lang, patient_id=c.patient_id, residency=c.residency)
        time.sleep(args.sleep)
        try:
            reply = orch.handle(state, c.text)
        except (AllProvidersFailed, LLMError) as e:
            stopped = f"{c.id}에서 중단: {str(e)[:120]}"
            break
        called = [t.name for t in reply.trace]
        missing = [t for t in c.must_call if t not in called]
        forbidden = [t for t in c.must_not_call if t in called]
        good = not missing and not forbidden
        ok += good
        done += 1
        provider = client.tracker.records[-1].model if client.tracker.records else ""
        rows.append(
            f"| {'O' if good else 'X'} | {c.id} | {c.lang} | {c.text[:50]} | {list(c.must_call)} / 금지 {list(c.must_not_call)} "
            f"| {called} | {provider} | {reply.text[:80].replace(chr(10), ' ')} |"
        )
    head = ["| 결과 | id | 언어 | 문장 | 기대(필수 / 금지) | 실제 호출 | 모델 | 답변 앞부분 |", "|---|---|---|---|---|---|---|---|"]
    return head + rows, ok, done, stopped


def save(kind: str, lines: list[str], ok: int, total: int, extra: str = "") -> Path:
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{date.today().isoformat()}-{kind}.md"
    body = [f"# 평가 결과 — {kind} ({date.today().isoformat()})", "", f"통과 {ok} / {total}", ""]
    if extra:
        body += [f"> {extra}", ""]
    path.write_text("\n".join(body + lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--safety", action="store_true")
    ap.add_argument("--intent", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--ids", default="")
    ap.add_argument("--sleep", type=float, default=6.0)
    args = ap.parse_args()
    if not (args.safety or args.intent):
        ap.error("--safety 또는 --intent")
    if args.safety:
        lines, ok, total = run_safety()
        print(save("safety", lines, ok, total), f"{ok}/{total}")
    if args.intent:
        lines, ok, total, stopped = run_intent(args)
        print(save("intent", lines, ok, total, stopped), f"{ok}/{total}", stopped)


if __name__ == "__main__":
    main()
