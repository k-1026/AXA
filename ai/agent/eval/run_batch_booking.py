"""예약에 필요한 칸을 한 번에 묻는지 — 기다리는 횟수 줄이기 (2026-11-26).

    LLM_PROVIDER_ORDER=nemotron python -m ai.agent.eval.run_batch_booking --tag nemotron

흐름: 병원 찾기 → (단기 방문 + 첫 번째 병원 선택) → 챗봇이 빠진 칸을 **한 메시지에** 묻는다 → 사용자가 한 줄로 다 답함 → 초안
전에는 날짜·언어·국적·비자·문의를 하나씩 물어 예약까지 5~6턴이었다. 가상 데이터만.
결과는 ai/agent/eval/results/날짜-batch-booking-태그.md
"""

from __future__ import annotations

import argparse
import time
from datetime import date
from pathlib import Path

from ai.agent.service import ChatService, PatientInfo, RateLimiter
from ai.agent.session_store import InMemorySessionStore
from ai.agent.tools.booking_store import BookingStore
from ai.llm.client import LLMClient

RESULTS = Path(__file__).parent / "results"
PATIENT = PatientInfo("demo-batch-1", "Asia/Taipei")

TURNS = [
    ("search", "I have acne scars and want treatment in Suseong-gu."),
    ("pick", "I'm just visiting Korea for a week. Let's book the first one."),
    ("answer", "December 4 at 10:00, in English, I'm from Taiwan, no visa help needed, and I want to ask about scar laser options."),
]
# 2턴 답에서 물어봐야 하는 칸 (영어 답 기준, 하나라도 보이면 그 칸을 물은 것으로 봄)
ASKED = {
    "date": ("date", "time", "when"),
    "language": ("language",),
    "nationality": ("nationality", "country", "from"),
    "visa": ("visa",),
    "inquiry": ("ask", "question", "inquiry", "would you like to"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    client = LLMClient.from_settings()
    service = ChatService(client, sessions=InMemorySessionStore(), bookings=BookingStore(),
                          limiter=RateLimiter(per_minute=1000, per_day=10000))
    log, turns, sid = [], {}, None
    for tid, text in TURNS:
        time.sleep(args.sleep)
        t0 = time.time()
        r = service.ask(PATIENT, sid, text, "en")
        sid = r.session_id
        turns[tid] = {"text": r.text, "cards": {c.type: c for c in r.cards}, "sec": time.time() - t0}
        log.append(f"**사용자:** {text}\n\n- 카드: {list(turns[tid]['cards'])} · {turns[tid]['sec']:.1f}초\n\n**챗봇:** {r.text}\n")

    low = turns["pick"]["text"].lower()
    asked = [k for k, words in ASKED.items() if any(w in low for w in words)]
    draft = turns["answer"]["cards"].get("booking_draft")
    req = draft.data.request if draft else {}
    first_id = None
    if "hospital_list" in turns["search"]["cards"]:
        first_id = turns["search"]["cards"]["hospital_list"].data.hospitals[0].hospital_id
    checks = [
        ("1. 병원을 고른 턴에서 빠진 칸을 한 메시지에 물었다 (5칸 중 4칸 이상)", len(asked) >= 4, f"물은 칸={asked}"),
        ("2. 2턴에서 초안을 미리 만들지 않았다 (값을 지어내지 않음)", "booking_draft" not in turns["pick"]["cards"], str(list(turns["pick"]["cards"]))),
        ("3. 한 줄 답 뒤에 바로 초안 카드가 나왔다 (3턴 만에)", draft is not None, str(list(turns["answer"]["cards"]))),
        ("4. 초안이 사용자 말과 맞다 (첫 번째 병원, 12/4 10:00, 영어, 대만, 비자 도움 없음)",
         bool(draft) and draft.data.hospital_id == first_id and req.get("preferred_slots") == ["2026-12-04T01:00:00Z"]
         and req.get("lang") == "en" and req.get("nationality") == "TW" and req.get("visa_needed") is False,
         f"병원={draft.data.hospital_id if draft else None}(첫 번째={first_id}) "
         f"{ {k: req.get(k) for k in ('preferred_slots', 'lang', 'nationality', 'visa_needed')} if draft else ''}"),
    ]
    passed = sum(ok for _, ok, _ in checks)
    out = RESULTS / f"{date.today().isoformat()}-batch-booking{('-' + args.tag) if args.tag else ''}.md"
    lines = [f"# 예약 칸 한 번에 묻기 ({args.tag or 'default'})", "",
             f"모델: {[p.model for p in client.providers]} · {passed}/{len(checks)} · "
             f"턴별 초: {[(k, round(v['sec'], 1)) for k, v in turns.items()]}", "",
             "| 결과 | 확인 항목 | 메모 |", "|---|---|---|",
             *[f"| {'O' if ok else 'X'} | {n} | {m.replace(chr(10), ' ').replace('|', '/')} |" for n, ok, m in checks],
             "", "## 대화", "", *log]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out, f"{passed}/{len(checks)}")
    for n, ok, m in checks:
        print("O" if ok else "X", n, "" if ok else f"- {m[:200]}")


if __name__ == "__main__":
    main()
