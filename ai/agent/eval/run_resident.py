"""국내 거주 계정 시나리오 — 첫 턴부터 예약·추천·찜을 권하지 않고, 예약 요청 턴에서 바로 안내하는지 (2026-11-26).

    LLM_PROVIDER_ORDER=nemotron python -m ai.agent.eval.run_resident --tag nemotron

계정 residency=resident (가입 때 거주국 대한민국). 사용자 말은 고정, 확인 항목별로 O/X.
가상 데이터만. 결과는 ai/agent/eval/results/날짜-resident-태그.md
"""

from __future__ import annotations

import argparse
import re
import time
from datetime import date
from pathlib import Path

from ai.agent.service import ChatService, PatientInfo, RateLimiter
from ai.agent.session_store import InMemorySessionStore
from ai.agent.tools.booking_store import BookingStore
from ai.llm.client import LLMClient

RESULTS = Path(__file__).parent / "results"
PATIENT = PatientInfo("demo-resident-1", "Asia/Seoul", "resident")

TURNS = [
    ("search", "수성구에서 여드름 흉터 치료하는 피부과 찾아줘"),
    ("recommend", "추천해 줘. 12월 4일 오전 10시에 상담 예약하고 싶어"),
    ("book", "첫 번째 병원으로 예약해 줘"),
]
# 예약·요청·찜을 "해 주겠다/할까요" 하는 표현. 안내 문장("단기 방문자만 가능")은 걸리지 않게 제안형만 본다
# "해 드릴 수 없습니다" 같은 거절 문장은 제외 (2026-11-26 오탐)
OFFER = re.compile(r"(상담\s*요청|예약|초안|찜|저장).{0,15}(도와\s*드릴|만들어\s*드릴|해\s*드릴|할까요|하시겠|진행해\s*드릴)(?!\s*수\s*(없|가\s*없))")
PHONE = re.compile(r"0\d{1,2}-\d{3,4}-\d{4}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    client = LLMClient.from_settings()
    service = ChatService(client, sessions=InMemorySessionStore(), bookings=BookingStore(),
                          limiter=RateLimiter(per_minute=1000, per_day=10000))
    used: list[str] = []
    run = service.orchestrator.registry.run

    def traced(name, a, ctx):
        r = run(name, a, ctx)
        used.append(f"{name}:{r.get('status', 'ok')}")
        return r

    service.orchestrator.registry.run = traced

    log, turns, sid = [], {}, None
    for tid, text in TURNS:
        time.sleep(args.sleep)
        used.clear()
        t0 = time.time()
        r = service.ask(PATIENT, sid, text, "ko")
        sid = r.session_id
        turns[tid] = {"text": r.text, "tools": list(used), "cards": [c.type for c in r.cards], "sec": time.time() - t0}
        log.append(f"**사용자:** {text}\n\n- 도구: {turns[tid]['tools']} · 카드: {turns[tid]['cards']} · {turns[tid]['sec']:.1f}초\n\n**챗봇:** {r.text}\n")

    checks = [
        ("1. 병원 찾기 턴: 목록은 보여 주고, 예약·요청·찜 제안이 없다",
         "hospital_list" in turns["search"]["cards"] and not OFFER.search(turns["search"]["text"]), turns["search"]["text"][-120:]),
        ("2. 추천·예약 요청 턴: 이 턴에서 바로 '단기 방문자만' 안내, 초안을 만들어 주겠다고 하지 않는다",
         ("단기" in turns["recommend"]["text"] or "직접" in turns["recommend"]["text"]) and not OFFER.search(turns["recommend"]["text"]),
         turns["recommend"]["text"][-160:]),
        ("3. 2턴에서 추천·요청서 도구를 부르지 않았다 (불렀어도 not_available만)",
         all(not u.startswith(("recommend_hospitals:ok", "prepare_booking_request:draft")) for u in turns["recommend"]["tools"]),
         str(turns["recommend"]["tools"])),
        ("4. 예약해 줘 턴: 직접 연락 안내 + 전화번호", "직접" in turns["book"]["text"] and bool(PHONE.search(turns["book"]["text"])),
         turns["book"]["text"][-160:]),
        ("4-1. '첫 번째 병원' = 1턴 목록의 첫 병원 (가상피부과의원 A, 053-000-0001)",
         "053-000-0001" in turns["book"]["text"] and "053-000-0002" not in turns["book"]["text"], turns["book"]["text"][-160:]),
        ("5. 어느 턴에도 요청서 초안 카드가 없다", all("booking_draft" not in t["cards"] for t in turns.values()), ""),
    ]

    passed = sum(ok for _, ok, _ in checks)
    out = RESULTS / f"{date.today().isoformat()}-resident{('-' + args.tag) if args.tag else ''}.md"
    lines = [f"# 국내 거주 계정 시나리오 ({args.tag or 'default'})", "",
             f"모델: {[p.model for p in client.providers]} · {passed}/{len(checks)} · "
             f"턴별 초: {[(k, round(v['sec'], 1)) for k, v in turns.items()]}", "",
             "| 결과 | 확인 항목 | 메모 |", "|---|---|---|",
             *[f"| {'O' if ok else 'X'} | {name} | {note.replace(chr(10), ' ').replace('|', '/')} |" for name, ok, note in checks],
             "", "## 대화", "", *log]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out, f"{passed}/{len(checks)}")
    for name, ok, note in checks:
        print("O" if ok else "X", name, "" if ok else f"- {note[:160]}")


if __name__ == "__main__":
    main()
