"""원스톱 시나리오 실행기 (plan.md 12-4의 6단계) — 실제 모델로 처음부터 끝까지.

    python -m ai.agent.eval.run_scenario --tag gemini
    LLM_PROVIDER_ORDER=nemotron python -m ai.agent.eval.run_scenario --tag nemotron

흐름: 흉터 상담 → 병원 목록 → 추천 → 체류 형태 → 예약 정보 채우기 → (환자가 제출) → 상태 조회 → (병원이 확정) → 상태 조회
- 사용자 말은 아래 TURNS에 고정. 모델이 다르게 반응해도 멈추지 않고 확인 항목별로 O/X를 적는다
- 제출·병원 확정은 챗봇이 아니라 코드가 한다 (화면 버튼·병원 대시보드 역할)
- 가상 데이터만 사용. 결과는 ai/agent/eval/results/날짜-scenario-태그.md 로 저장
"""

from __future__ import annotations

import argparse
import time
from datetime import date
from pathlib import Path

from ai.agent.core.orchestrator import ConversationState, Orchestrator
from ai.agent.tools.booking_store import required_consents
from ai.agent.tools.chat_tools import build_registry
from ai.llm.client import LLMClient
from ai.llm.retry import LLMError

RESULTS = Path(__file__).parent / "results"

# (id, 사용자 말). 영어 사용자, 대만 국적, 12월 4일 희망
TURNS = [
    ("scar", "I have acne scars and want treatment in Suseong-gu. I only speak English."),
    ("recommend", "Please recommend one for me. I'd like to go on December 4th."),
    ("residency", "I'm just visiting Korea for a week."),
    ("book", "Let's book the first one on December 4 at 10:00. I want to ask about scar laser options."),
    ("nationality", "I'm from Taiwan."),
    ("visa", "No, I don't need help with a visa."),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--sleep", type=float, default=4.0)
    args = ap.parse_args()

    client = LLMClient.from_settings()
    orch = Orchestrator(client, build_registry())
    state = ConversationState(language="en", patient_id="demo-patient-2", timezone="Asia/Taipei")

    log: list[str] = []
    checks: list[tuple[str, bool, str]] = []
    called: dict[str, list[str]] = {}

    def say(user_id: str, text: str) -> None:
        time.sleep(args.sleep)
        reply = orch.handle(state, text)
        names = [t.name for t in reply.trace]
        called[user_id] = names
        log.append(f"**사용자:** {text}\n\n- 호출한 도구: {names}\n- 카드: {[c['type'] for c in reply.cards]}\n"
                   f"- 초안 있음: {state.booking_draft is not None} · 체류 형태 기록: {state.residency}\n\n**챗봇:** {reply.text}\n")

    try:
        for uid, text in TURNS:
            say(uid, text)

        draft = state.booking_draft
        checks.append(("1. 병원 찾기·추천 도구를 불렀다", any(t in called["scar"] + called["recommend"] + called["residency"]
                                                          for t in ("search_hospitals", "recommend_hospitals")), str(called)))
        checks.append(("2. 체류 형태는 사용자가 말한 뒤에 기록됐다", called["recommend"].count("record_residency") == 0
                       and state.residency == "short_term", f"기록={state.residency}, 추천 턴 호출={called['recommend']}"))
        checks.append(("3. 요청서 초안이 만들어졌다", draft is not None, str(draft)[:200]))
        checks.append(("4. 챗봇은 제출하지 않았다 (저장소에 요청 없음)", orch.store.list_for_patient("demo-patient-2") == [], ""))

        if draft is not None:
            checks.append(("5. 초안 내용이 사용자 말과 맞다", draft.get("nationality") == "TW" and draft.get("visa_needed") is False
                           and draft.get("preferred_slots") == ["2026-12-04 10:00"] and draft.get("language") == "en",
                           str({k: draft.get(k) for k in ("hospital_id", "department", "preferred_slots", "language", "nationality", "visa_needed", "inquiry")})))
            no_consent = orch.submit_draft(state, [{"kind": "privacy", "version": "v1"}])
            checks.append(("6. 동의가 모자라면 제출이 거절된다", (not no_consent.ok) and no_consent.error["code"] == "consent.required", str(no_consent.error)))
            # 화면 카드에 적힌 필수 동의를 환자가 모두 체크하는 것과 같다 (초안마다 다름: 건강정보가 있으면 health 추가)
            needed = required_consents(draft)
            log.append(f"**[카드에 표시된 필수 동의]** {needed} · 초안의 health_info: {draft.get('health_info')!r}\n")
            result = orch.submit_draft(state, [{"kind": k, "version": "v1"} for k in needed])
            checks.append(("7. 환자가 [제출]하면 pending 요청이 생긴다", result.ok and result.booking["status"] == "pending", result.text or str(result.error)))
            log.append(f"**[환자가 제출 버튼을 누름]** → {result.text or result.error}\n")
            if result.ok:
                say("status1", "Did my request go through?")
                rows = [c for c in orch.store.list_for_patient("demo-patient-2")]
                checks.append(("8. 상태 질문에 get_my_bookings를 불렀다", "get_my_bookings" in called["status1"], str(called["status1"])))
                orch.store.hospital_respond(result.booking["id"], "confirm")
                log.append("**[병원 직원이 대시보드에서 확정]**\n")
                say("status2", "Any update from the hospital?")
                checks.append(("9. 병원 확정 후 상태 질문에 다시 조회했다", "get_my_bookings" in called["status2"], str(called["status2"])))
                checks.append(("10. 저장소 상태가 confirmed", rows and orch.store.list_for_patient("demo-patient-2")[0]["status"] == "confirmed", ""))
    except LLMError as e:
        log.append(f"**중단:** {str(e)[:200]}\n")
        checks.append(("중단 없이 끝까지 진행", False, str(e)[:160]))

    ok = sum(1 for _, good, _ in checks if good)
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{date.today().isoformat()}-scenario{'-' + args.tag if args.tag else ''}.md"
    used = sorted({(r.provider, r.model) for r in client.tracker.records if r.ok})
    body = [f"# 원스톱 시나리오 — {date.today().isoformat()} {args.tag}", "", f"확인 항목 통과 {ok} / {len(checks)}",
            f"> 사용한 모델: {used}. 가상 데이터. 제출·병원 확정은 코드가 대신함", "",
            "| 결과 | 확인 항목 | 메모 |", "|---|---|---|"]
    body += [f"| {'O' if good else 'X'} | {name} | {note[:150]} |" for name, good, note in checks]
    body += ["", "## 대화 기록", "", *log]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(path, f"{ok}/{len(checks)}")
    for name, good, note in checks:
        print("O" if good else "X", name)


if __name__ == "__main__":
    main()
