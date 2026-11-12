"""원스톱 시나리오 실행기 — **서비스 층(ChatService)을 거쳐** 실제 모델로 처음부터 끝까지 (plan.md 12-4 6·7단계).

    python -m ai.agent.eval.run_scenario --tag gemini
    LLM_PROVIDER_ORDER=nemotron python -m ai.agent.eval.run_scenario --tag nemotron

흐름: 흉터 상담 → 병원 목록 → 추천 → 체류 형태 → 예약 정보 채우기 → (프론트가 기존 예약 요청 API로 제출) → 상태 조회 → (병원이 확정) → 상태 조회
- 대화는 매 턴 **저장소에서 텍스트만** 다시 불러 이어 간다 (도구 호출·결과는 저장하지 않음) → "첫 번째 병원" 같은 말이 상태로 이어지는지 확인
- 제출은 카드의 `request` + `consents`를 사람이 쓰는 요청서와 같은 호출(`create_from_payload`)로 보낸다. 챗봇은 제출하지 않는다
- 사용자 말은 TURNS에 고정. 모델이 달리 반응해도 멈추지 않고 확인 항목별로 O/X를 적는다
- 가상 데이터만. 결과는 ai/agent/eval/results/날짜-scenario-태그.md
"""

from __future__ import annotations

import argparse
import time
from datetime import date, datetime, timezone
from pathlib import Path

from ai.agent.service import DRAFT_KEPT_KEYS, ChatService, ChatServiceError, PatientInfo, RateLimiter
from ai.agent.session_store import InMemorySessionStore
from ai.agent.tools.booking_store import BookingStore
from ai.llm.client import LLMClient

RESULTS = Path(__file__).parent / "results"
PATIENT = PatientInfo("demo-patient-2", "Asia/Taipei")
OTHER = PatientInfo("demo-patient-3", "Asia/Seoul")  # 다른 계정: 남의 세션에 접근하면 not_found여야 함

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
    ap.add_argument("--sleep", type=float, default=3.0)
    args = ap.parse_args()

    client = LLMClient.from_settings()
    sessions, bookings = InMemorySessionStore(), BookingStore()
    service = ChatService(client, sessions=sessions, bookings=bookings, limiter=RateLimiter(per_minute=1000, per_day=10000))

    log: list[str] = []
    checks: list[tuple[str, bool, str]] = []
    cards_by_turn: dict[str, list[str]] = {}
    session_id: str | None = None
    timings: list[tuple[str, float, int]] = []
    last_cards: dict[str, object] = {}
    saved_drafts: list[dict] = []  # 턴마다 서버에 저장된 초안 (health_info·inquiry가 빠져야 함)

    def say(turn_id: str, text: str):
        nonlocal session_id
        time.sleep(args.sleep)
        before = len([r for r in client.tracker.records if r.ok])
        t0 = time.time()
        r = service.ask(PATIENT, session_id, text, "en")
        timings.append((turn_id, time.time() - t0, len([x for x in client.tracker.records if x.ok]) - before))
        session_id = r.session_id
        cards_by_turn[turn_id] = [c.type for c in r.cards]
        last_cards.update({c.type: c for c in r.cards})
        state = sessions.get(PATIENT.patient_id, session_id).state
        if state.get("draft"):
            saved_drafts.append(dict(state["draft"]))
        log.append(f"**사용자:** {text}\n\n- 카드: {cards_by_turn[turn_id]}\n- 저장된 상태: 체류 형태={state.get('residency')}, 초안 있음={'draft' in state}, "
                   f"보여 준 병원={[h['id'] for h in state.get('shown_hospitals', [])]}\n\n**챗봇:** {r.text}\n")
        return r, state

    residency_after: dict[str, str | None] = {}
    try:
        for tid, text in TURNS:
            _, st = say(tid, text)
            residency_after[tid] = st.get("residency")

        draft_card = last_cards.get("booking_draft")
        all_cards = [t for ts in cards_by_turn.values() for t in ts]
        checks.append(("1. 병원 목록·추천 카드가 나왔다", "hospital_list" in all_cards or "hospital_suggestions" in all_cards, str(cards_by_turn)))
        checks.append(("2. 체류 형태는 사용자가 말한 뒤에만 저장됐다",
                       residency_after["scar"] is None and residency_after["recommend"] is None and residency_after["residency"] == "short_term",
                       str(residency_after)))
        checks.append(("3. 요청서 초안 카드가 나왔다", draft_card is not None, str(cards_by_turn)))
        checks.append(("4. 챗봇은 제출하지 않았다 (내 요청 0건)", bookings.list_for_patient(PATIENT.patient_id) == [], ""))
        stored = sessions.messages(session_id, 100)
        checks.append(("5. 저장소에는 사용자·챗봇 텍스트만 있다", {m.role for m in stored} == {"user", "assistant"} and len(stored) == 2 * len(TURNS),
                       f"{len(stored)}개"))

        if draft_card is not None:
            d, req = draft_card.data.draft, draft_card.data.request
            shown = sessions.get(PATIENT.patient_id, session_id).state.get("shown_hospitals", [])
            first_id = shown[0]["id"] if shown else None
            checks.append(("6. 초안이 사용자 말과 맞다 (첫 번째 병원, 12/4 10:00, 대만, 비자 도움 없음)",
                           d.get("hospital_id") == first_id and req["preferred_slots"] == ["2026-12-04T01:00:00Z"]
                           and req["nationality"] == "TW" and req["visa_needed"] is False and req["department_code"] == "dermatology",
                           f"병원={d.get('hospital_id')}(첫 번째={first_id}) request={ {k: req[k] for k in ('department_code', 'preferred_slots', 'lang', 'nationality', 'visa_needed')} }"))
            # 프론트: 카드의 request + 동의를 사람이 쓰는 요청서와 같은 API로 보낸다
            from ai.agent.tools.booking_store import BookingError

            try:
                bookings.create_from_payload(PATIENT.patient_id, draft_card.data.hospital_id, req, [{"kind": "privacy", "version": "v1"}],
                                             today=datetime.now(timezone.utc))
                insufficient = "동의 없이 생성됨"
            except BookingError as e:
                insufficient = e.code
            checks.append(("7. 동의가 모자라면 같은 API가 거절한다", insufficient == "consent.required", insufficient))
            consents = [{"kind": k, "version": "v1"} for k in draft_card.data.consents_required]
            booking = bookings.create_from_payload(PATIENT.patient_id, draft_card.data.hospital_id, req, consents, today=datetime.now(timezone.utc))
            log.append(f"**[프론트가 기존 예약 요청 API로 제출]** 동의={draft_card.data.consents_required} → {booking['id']} ({booking['status']})\n")
            checks.append(("8. 같은 API로 제출하면 pending 요청이 생긴다", booking["status"] == "pending", booking["id"]))

            r, st = say("status1", "Did my request go through?")
            cards = {c.type: c for c in r.cards}
            shown_status = [b.status for b in cards["booking_list"].data.bookings] if "booking_list" in cards else None
            # 서버가 맥락으로 "제출됨(pending)"을 알려 주므로 모델은 도구를 다시 부르지 않고 답해도 맞다 → 카드 또는 답변 내용으로 확인
            says_pending = "pending" in r.text.lower() or "대기" in r.text
            checks.append(("9. 다음 대화에서 제출을 알아보고 초안을 닫았다 (pending으로 답함)",
                           "draft" not in st and (shown_status == ["pending"] or says_pending),
                           f"초안 남음={'draft' in st}, 상태 카드={shown_status}, 답변에 pending={says_pending}"))

            bookings.hospital_respond(booking["id"], "confirm")
            log.append("**[병원 직원이 대시보드에서 확정]**\n")
            r, _ = say("status2", "Any update from the hospital?")
            cards = {c.type: c for c in r.cards}
            shown_status = [b.status for b in cards["booking_list"].data.bookings] if "booking_list" in cards else None
            checks.append(("10. 병원 확정 후 상태 질문에 confirmed로 답했다", shown_status == ["confirmed"], str(shown_status)))

            leaked = sorted({k for d in saved_drafts for k in d if k not in DRAFT_KEPT_KEYS})
            checks.append(("11. 서버에 저장된 초안에 health_info·inquiry가 없다 (화면 카드의 request.message에는 문의 내용이 있다)",
                           bool(saved_drafts) and not leaked and bool(req.get("message")),
                           f"저장된 초안 {len(saved_drafts)}번, 허용 밖 키={leaked}, 카드 message(문의) 있음={bool(req.get("message"))}"))

        # 다른 계정이 이 세션을 이어 쓰거나 지우려 하면 not_found, 내 세션은 그대로
        results = []
        for action in ("ask", "delete"):
            try:
                if action == "ask":
                    service.ask(OTHER, session_id, "Show me the previous conversation.", "en")
                else:
                    service.delete_session(OTHER, session_id)
                results.append(f"{action}=허용됨")
            except ChatServiceError as e:
                results.append(f"{action}={e.status} {e.code}")
        still_mine = sessions.get(PATIENT.patient_id, session_id) is not None
        checks.append(("12. 다른 계정의 세션 접근(이어 쓰기·삭제)은 거절되고 내 세션은 남는다",
                       results == ["ask=404 not_found", "delete=404 not_found"] and still_mine and sessions.get(OTHER.patient_id, session_id) is None,
                       f"{results}, 내 세션 남음={still_mine}"))
    except ChatServiceError as e:
        log.append(f"**중단:** {e.status} {e.code} {e.message}\n")
        checks.append(("중단 없이 끝까지 진행", False, f"{e.code}: {e.message}"))

    ok = sum(1 for _, good, _ in checks if good)
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{date.today().isoformat()}-scenario{'-' + args.tag if args.tag else ''}.md"
    used = sorted({(r.provider, r.model) for r in client.tracker.records if r.ok})
    calls = sum(n for _, _, n in timings)
    tokens = sum(r.prompt_tokens for r in client.tracker.records if r.ok)
    body = [f"# 원스톱 시나리오 (서비스 층 경유) — {date.today().isoformat()} {args.tag}", "", f"확인 항목 통과 {ok} / {len(checks)}",
            f"> 사용한 모델: {used}. 가상 데이터. 대화는 저장소의 텍스트만으로 이어 감. 제출은 기존 예약 요청 API 호출을 코드가 대신함", "",
            f"턴별 (초 / LLM 호출): {[(t, round(s, 1), n) for t, s, n in timings]} · 합계 호출 {calls}회, 입력 토큰 {tokens}", "",
            "| 결과 | 확인 항목 | 메모 |", "|---|---|---|"]
    body += [f"| {'O' if good else 'X'} | {name} | {note[:200]} |" for name, good, note in checks]
    body += ["", "## 대화 기록", "", *log]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(path, f"{ok}/{len(checks)}", f"LLM 호출 {calls}회, 입력 토큰 {tokens}")
    for name, good, note in checks:
        print("O" if good else "X", name, "" if good else f"— {note[:160]}")


if __name__ == "__main__":
    main()
