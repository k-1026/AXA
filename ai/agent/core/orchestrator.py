"""챗봇 오케스트레이터 — 사용자 메시지 1개를 받아 도구를 골라 부르고 답 + 카드를 돌려준다.

흐름 (subject/plan.md 12-3)
    사용자 메시지 → (앞단 안전 검사 safety.check) → LLM이 도구 선택 → 도구 실행 → 결과를 LLM에 돌려줌 → … → 최종 답
- 도구 호출은 한 턴에 max_steps번까지. 넘으면 도구 없이 답만 받는다
- 화면 카드는 **도구 결과에서 코드가 만든다** (LLM이 숫자·병원 정보를 다시 쓰지 않음)
- 대화 상태(ConversationState)는 호출하는 쪽(백엔드)이 저장·복원한다. 여기서는 메모리 객체만 다룸
- 챗봇(handle)은 요청서 **초안**(state.booking_draft)까지만 만든다. 제출은 환자가 화면의 [제출] 버튼을 눌렀을 때
  앱이 `submit_draft()`를 부른다 (LLM이 부르는 도구가 아님 → 모델이 마음대로 제출할 수 없다)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Any, Callable, Protocol

from ai.agent.prompts.orchestrator import build_system_prompt
from ai.agent.tools.booking_store import BookingError, BookingGateway, BookingStore
from ai.agent.tools.registry import JSON, ToolContext, ToolRegistry
from ai.llm import safety
from ai.llm.client import LLMResponse, Message, tool_result_message

# 도구 이름 → 화면 카드 종류. 결과가 오류이거나 비어 있으면 카드를 만들지 않는다
CARD_TYPES = {
    "search_hospitals": "hospital_list",
    "recommend_hospitals": "hospital_suggestions",
    "get_hospital": "hospital_detail",
    "get_prices": "price_list",
    "retrieve_docs": "sources",
    "check_availability": "time_slots",
    "prepare_booking_request": "booking_draft",
    "get_my_bookings": "booking_list",
    "open_aftercare_thread": "aftercare_thread",
}


class ChatLLM(Protocol):
    def chat(self, messages: list[Message], *, tools=None, service: str = ..., **kwargs) -> LLMResponse: ...


@dataclass
class ConversationState:
    language: str = "en"
    patient_id: str | None = None
    residency: str | None = None  # "short_term" | "resident" | None
    history: list[Message] = field(default_factory=list)  # system 메시지 제외
    booking_draft: JSON | None = None  # 마지막으로 만든 요청서 초안 (제출 전)
    timezone: str = "UTC"  # 환자 프로필의 IANA 시간대 (요청서 patient_timezone)


@dataclass
class SubmitResult:
    ok: bool
    booking: JSON | None = None
    text: str = ""
    error: JSON | None = None  # {"code", "message", "detail"} — 코드는 docs/backend-contracts.md 4절과 같음


@dataclass
class ToolTrace:
    name: str
    arguments: JSON
    ok: bool


@dataclass
class ChatReply:
    text: str
    cards: list[JSON]
    trace: list[ToolTrace]
    ai_generated: bool = True  # 화면에 "AI 생성" 표시 (인공지능기본법 제31조, docs/agent-spec.md)
    blocked: bool = False  # 앞단 검사에서 막힌 경우 (응급 → 119 안내)
    safety_categories: list[str] = field(default_factory=list)  # 앞단 검사가 붙인 분류 (기록·통계용)
    medical_notice: bool = False  # 화면에 "의료 상담이 아닙니다" 고지를 함께 보여줄지
    truncated: bool = False  # 도구 호출 한도에 걸린 경우
    user_text: str = ""  # 개인정보를 가린 사용자 메시지 (저장용). 응급이면 원문 대신 "[emergency message]"


def _card(tool: str, result: JSON) -> JSON | None:
    kind = CARD_TYPES.get(tool)
    if not kind or "error" in result:
        return None
    if tool == "prepare_booking_request" and result.get("status") != "draft":
        return None
    if tool == "open_aftercare_thread" and result.get("status") != "opened":
        return None
    if tool == "search_hospitals" and not result.get("hospitals"):
        return None
    if tool == "recommend_hospitals" and not result.get("suggestions"):
        return None
    if tool == "get_prices" and not result.get("prices"):
        return None
    if tool == "retrieve_docs" and not result.get("documents"):
        return None
    if tool == "get_my_bookings" and not result.get("bookings"):
        return None
    if tool == "check_availability" and not result.get("slots"):
        return None
    return {"type": kind, "data": {k: v for k, v in result.items() if not k.startswith("_")}}


def _trim(history: list[Message], max_messages: int) -> list[Message]:
    """오래된 턴부터 버린다. 도구 호출·결과 쌍이 끊기지 않게 user 메시지 경계에서만 자른다."""
    if len(history) <= max_messages:
        return history
    starts = [i for i, m in enumerate(history) if m["role"] == "user"]
    for i in starts:
        if len(history) - i <= max_messages:
            return history[i:]
    return history[starts[-1]:] if starts else history


class Orchestrator:
    def __init__(
        self,
        llm: ChatLLM,
        registry: ToolRegistry,
        *,
        max_steps: int = 5,
        max_history: int = 40,
        safety_check: Callable[[str, str], safety.SafetyResult] | None = safety.check,
        today: Callable[[], date] = date.today,
        store: BookingGateway | None = None,
    ):
        self.store = store or BookingStore()  # 백엔드 booking.service가 생기면 교체
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.max_history = max_history
        self.safety_check = safety_check  # ai/llm/safety.py — None이면 검사 없이 통과 (테스트용)
        self._today = today

    def submit_draft(self, state: ConversationState, consents: list[JSON]) -> SubmitResult:
        """환자가 요청서 카드의 [제출]을 눌렀을 때 앱이 부른다. consents = [{"kind": "privacy", "version": "v1"}, ...]

        성공하면 pending 요청이 생기고 초안은 비워진다. 대화 기록에 제출 사실을 남겨, 다음 턴에 모델이
        "보냈다/안 보냈다"를 정확히 알게 한다.
        """
        if not hasattr(self.store, "create_request"):  # 서비스가 주입한 읽기 전용 게이트웨이
            raise NotImplementedError("submit_draft는 eval·시연 전용(BookingStore 필요). 서비스는 프론트가 "
                                      "POST /hospitals/{id}/booking-requests 로 제출한다")
        draft = state.booking_draft
        if draft is None:
            return SubmitResult(False, error=BookingError("validation", "제출할 요청서 초안이 없습니다").as_dict())
        now = datetime.combine(self._today(), time(), tzinfo=timezone.utc)
        try:
            booking = self.store.create_request(
                state.patient_id, draft, consents, residency=state.residency,
                patient_timezone=state.timezone, today=now,
            )
        except BookingError as e:
            return SubmitResult(False, error=e.as_dict())
        state.booking_draft = None
        text = (f"[Submitted] The consultation request to {booking['hospital_name_en']} was submitted "
                f"(id {booking['id']}, status: pending). The hospital will confirm, decline, or propose another time.")
        if state.history and state.history[-1]["role"] == "assistant" and not state.history[-1].get("tool_calls"):
            state.history[-1] = {**state.history[-1], "content": f"{state.history[-1]['content']}\n{text}"}  # 연속 assistant 메시지 방지
        else:
            state.history.append({"role": "assistant", "content": text})
        return SubmitResult(True, booking=booking, text=text)

    def handle(self, state: ConversationState, user_text: str, extra_context: str | None = None) -> ChatReply:
        """extra_context: 이번 턴에만 시스템 프롬프트에 덧붙이는 맥락 (보여 준 병원 목록, 요청서 초안, 제출 알림 등)."""
        verdict = self.safety_check(user_text, state.language) if self.safety_check else None
        if verdict and verdict.action == "block":
            # 응급: LLM 호출 없이 고정 문구. 기록에는 원문 대신 표시만 남긴다
            state.history += [
                {"role": "user", "content": "[emergency message]"},
                {"role": "assistant", "content": verdict.reply},
            ]
            return ChatReply(
                text=verdict.reply, cards=[], trace=[], blocked=True, ai_generated=False,
                safety_categories=verdict.categories, user_text="[emergency message]",
            )
        if verdict:
            user_text = verdict.text  # 개인정보 마스킹된 글만 LLM·기록·도구에 전달
        guard_note = verdict.note if verdict and verdict.action == "guard" else None
        categories = verdict.categories if verdict else []

        ctx = ToolContext(
            patient_id=state.patient_id, language=state.language, residency=state.residency, last_user_text=user_text,
            timezone=state.timezone, store=self.store, today=self._today(),
        )
        system = {
            "role": "system",
            "content": build_system_prompt(
                today=self._today().isoformat(),
                language=state.language,
                logged_in=bool(state.patient_id),
                residency=state.residency,
                extra_context=extra_context,
            ),
        }
        turn: list[Message] = [{"role": "user", "content": user_text}]
        base = _trim(state.history, self.max_history)
        specs = self.registry.openai_specs()
        cards: list[JSON] = []
        trace: list[ToolTrace] = []
        truncated = False

        def ask(with_tools: bool) -> LLMResponse:
            # guard 지시는 이번 턴 호출에만 붙이고 대화 기록에는 남기지 않는다
            extra = [{"role": "system", "content": guard_note}] if guard_note else []
            msgs = [system, *base, *extra, *turn]
            return self.llm.chat(msgs, tools=specs if with_tools else None, service="chatbot")

        res = ask(True)
        steps = 0
        while res.tool_calls:
            if steps >= self.max_steps:
                truncated = True
                break
            steps += 1
            turn.append(res.as_assistant_message())
            for tc in res.tool_calls:
                result = self.registry.run(tc.name, tc.arguments, ctx)
                trace.append(ToolTrace(tc.name, tc.arguments, ok="error" not in result))
                turn.append(tool_result_message(tc.id, tc.name, result))
                if card := _card(tc.name, result):
                    cards = [c for c in cards if c["type"] != card["type"]] + [card]  # 같은 종류는 최신 것만
                    if card["type"] == "booking_draft":
                        state.booking_draft = card["data"]["draft"]
            res = ask(True)

        if truncated:
            # 도구를 더 부르려 했지만 한도 → 호출 요청은 버리고, 지금까지 결과로만 답하게 한다
            turn.append({"role": "user", "content": "(system) Tool limit reached. Answer now with what you have, and say what is still missing."})
            res = ask(False)
            turn.pop()

        text = (res.text or "").strip()
        turn.append({"role": "assistant", "content": text})
        state.residency = ctx.residency  # record_residency가 바꿨을 수 있음
        state.history = base + turn
        return ChatReply(
            text=text, cards=cards, trace=trace, truncated=truncated,
            safety_categories=categories, medical_notice=bool(categories), user_text=user_text,
        )
