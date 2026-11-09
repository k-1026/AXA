"""챗봇(오케스트레이터)이 부르는 환자 쪽 도구 9개 — 지금은 가짜 응답 (fake_data.py).

| 의도 | 도구 |
|---|---|
| 진료과안내 | suggest_department |
| 병원찾기 | search_hospitals, get_hospital |
| 가격 | get_prices |
| 정보질문 | retrieve_docs |
| 예약 | check_availability, prepare_booking_request |
| 예약상태 | get_my_bookings |
| 사후문의 | open_aftercare_thread |

규칙 (docs/agent-spec.md, subject/plan.md 12절)
- 병원은 항상 **여러 곳을 이름순(중립)** 으로. 순위·평가·"추천" 없음
- prepare_booking_request는 **초안 카드만** 만든다. 제출은 환자가 화면 버튼으로 (도구로 제출 X)
- 국내 거주 외국인(resident)은 상담 예약 연결 불가 → 병원 연락처만 안내
- 사후 문의는 비의료 주제만 (의료 상담은 2027-05-27 외국인환자 비대면진료 시행 후 확장)
- 진료과 안내는 일반 정보 + "진단은 의료진 확인" 고지
"""

from __future__ import annotations

from datetime import date

from ai.agent.tools import fake_data as fd
from ai.agent.tools.registry import JSON, Tool, ToolContext, ToolError, ToolRegistry

LANGS = ["en", "zh", "zh-TW", "vi", "ja", "th", "ru", "ko"]
DISTRICTS = ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
AFTERCARE_TOPICS = ["schedule", "cost", "documents", "accommodation", "other_non_medical"]
DOC_TOPICS = ["visa", "procedure", "rights", "payment", "other"]

MEDICAL_DISCLAIMER = "General information only. Diagnosis and suitable treatment must be decided by a doctor."
NEUTRAL_NOTE = "Listed in name order. This is not a recommendation or ranking."
PRICE_NOTE = "Public non-covered fee notice for Korean patients (demo values). Final cost may differ; ask the hospital."


def _hospital_card(h: dict) -> JSON:
    return {
        "hospital_id": h["id"],
        "name_ko": h["name_ko"],
        "name_en": h["name_en"],
        "district": h["district"],
        "departments": h["departments"],
        "is_registered_facility": h["is_registered_facility"],
        # 번역 가능 병원 표시 (plan 12-1 #5): 직원 직접 응대 언어와 AI 번역 채팅을 구분
        "staff_languages": h["staff_languages"],
        "ai_translation_chat": h["ai_translation_chat"],
    }


def _find_hospital(hospital_id: int) -> dict:
    for h in fd.HOSPITALS:
        if h["id"] == hospital_id:
            return h
    raise ToolError(f"병원 {hospital_id}을(를) 찾을 수 없습니다")


def _parse_date(s: str, key: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise ToolError(f"'{key}'는 YYYY-MM-DD 형식이어야 합니다: {s}") from e


# ---------------------------------------------------------------- 핸들러
def suggest_department(args: JSON, ctx: ToolContext) -> JSON:
    concern = args["concern"].lower()
    found: list[str] = []
    for row in fd.DEPARTMENT_GUIDE:
        if any(k.lower() in concern for k in row["keywords"]):
            found += [d for d in row["departments"] if d not in found]
    return {
        "departments": found,
        "matched": bool(found),
        "note": MEDICAL_DISCLAIMER if found else "No matching department in the guide. Ask the user which department they want.",
    }


def search_hospitals(args: JSON, ctx: ToolContext) -> JSON:
    dept = args["department"]
    rows = [h for h in fd.HOSPITALS if dept in h["departments"]]
    if args.get("district"):
        rows = [h for h in rows if h["district"] == args["district"]]
    if args.get("registered_only", True):
        rows = [h for h in rows if h["is_registered_facility"]]
    if lang := args.get("language"):
        rows = [h for h in rows if lang in h["staff_languages"] or h["ai_translation_chat"]]
    if day := args.get("open_on"):
        rows = [h for h in rows if h["hours"].get(day)]
    rows.sort(key=lambda h: h["name_en"])  # 중립 정렬
    limit = args.get("limit", 5)
    return {"count": len(rows), "hospitals": [_hospital_card(h) for h in rows[:limit]], "note": NEUTRAL_NOTE}


def get_hospital(args: JSON, ctx: ToolContext) -> JSON:
    h = _find_hospital(args["hospital_id"])
    return {**_hospital_card(h), "hours": h["hours"], "address_en": h["address_en"], "tel": h["tel"],
            "hours_source": "demo", "can_request_consultation": h["is_registered_facility"]}


def get_prices(args: JSON, ctx: ToolContext) -> JSON:
    rows = fd.PRICES
    if hid := args.get("hospital_id"):
        rows = [p for p in rows if p["hospital_id"] == hid]
    if kw := args.get("item"):
        k = kw.lower()
        rows = [p for p in rows if k in p["item"].lower() or k in p["item_en"].lower()]
    return {"prices": [{**p, "currency": "KRW"} for p in rows], "note": PRICE_NOTE}


def retrieve_docs(args: JSON, ctx: ToolContext) -> JSON:
    q = args["query"].lower()
    topic = args.get("topic")
    rows = [d for d in fd.DOCS if (topic in (None, "other") or d["topic"] == topic)]
    if topic in (None, "other"):
        rows = [d for d in rows if any(w in (d["title"] + d["text"]).lower() for w in q.split())] or []
    if not rows:
        return {"documents": [], "note": "No document found. Say you don't know; do not answer from memory."}
    return {"documents": rows, "note": "Answer only from these documents and show source and as_of."}


def check_availability(args: JSON, ctx: ToolContext) -> JSON:
    h = _find_hospital(args["hospital_id"])
    start = _parse_date(args["date_from"], "date_from")
    end = _parse_date(args.get("date_to") or args["date_from"], "date_to")
    if end < start:
        raise ToolError("date_to가 date_from보다 빠릅니다")
    slots = {d: t for d, t in fd.AVAILABILITY.get(h["id"], {}).items() if start <= date.fromisoformat(d) <= end}
    return {"hospital_id": h["id"], "slots": slots,
            "note": "Times are candidates only. The hospital confirms the booking."}


def prepare_booking_request(args: JSON, ctx: ToolContext) -> JSON:
    if ctx.residency is None:
        return {"status": "needs_info", "ask": "residency",
                "question": "Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?"}
    h = _find_hospital(args["hospital_id"])
    if ctx.residency == "resident":
        return {"status": "not_available",
                "reason": "Consultation requests through MediDaegu are for short-term visitors. Please contact the hospital directly.",
                "hospital_tel": h["tel"]}
    if not h["is_registered_facility"]:
        return {"status": "not_available",
                "reason": "This hospital is not a registered foreign-patient facility, so requests can't be sent here.",
                "hospital_tel": h["tel"]}
    missing = [k for k in ("preferred_slots", "language", "inquiry") if not args.get(k)]
    if missing:
        return {"status": "needs_info", "missing": missing}
    return {
        "status": "draft",  # 아직 제출 아님
        "requires_patient_confirmation": True,  # 화면의 [제출] 버튼을 환자가 눌러야 pending 생성
        "draft": {
            "hospital_id": h["id"], "hospital_name_en": h["name_en"],
            "preferred_slots": args["preferred_slots"], "language": args["language"],
            "inquiry": args["inquiry"], "needs_interpreter": args.get("needs_interpreter", False),
        },
        "consents_required": ["privacy_and_transfer_to_hospital"],
        "consents_optional": ["health_information"],  # 건강정보는 별도 동의 (개인정보보호법 제23조)
        "note": "Show the summary card. Do not say the request was sent until the user presses Submit.",
    }


def get_my_bookings(args: JSON, ctx: ToolContext) -> JSON:
    if not ctx.patient_id:
        return {"status": "login_required"}
    rows = [b for b in fd.BOOKINGS if b["patient_id"] == ctx.patient_id]
    if st := args.get("status"):
        rows = [b for b in rows if b["status"] == st]
    names = {h["id"]: h["name_en"] for h in fd.HOSPITALS}
    return {"bookings": [{**b, "hospital_name_en": names.get(b["hospital_id"])} for b in rows]}


def open_aftercare_thread(args: JSON, ctx: ToolContext) -> JSON:
    if not ctx.patient_id:
        return {"status": "login_required"}
    bk = next((b for b in fd.BOOKINGS if b["id"] == args["booking_id"] and b["patient_id"] == ctx.patient_id), None)
    if bk is None:
        raise ToolError("내 예약에서 해당 booking_id를 찾을 수 없습니다")
    if not bk.get("visited"):
        return {"status": "not_available", "reason": "Follow-up chat opens after the visit."}
    return {
        "status": "opened", "thread_id": f"demo-thread-{bk['id']}", "hospital_id": bk["hospital_id"],
        "topic": args["topic"], "first_message": args["message"],
        "notice": "For schedule, cost, documents or accommodation questions only. This is not medical consultation.",
    }


# ---------------------------------------------------------------- 등록
def build_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register(Tool(
        "suggest_department",
        "사용자가 말한 고민(예: 여드름 흉터, 임플란트, 건강검진)을 **보통 다루는 진료과**를 일반 정보로 알려준다. "
        "진단·적합한 시술 판단은 하지 않는다. 결과의 진료과로 search_hospitals를 이어서 부를 수 있다.",
        {"type": "object", "properties": {
            "concern": {"type": "string", "description": "사용자가 말한 고민 원문 (사용자 언어 그대로)"}},
         "required": ["concern"]},
        suggest_department, "진료과안내"))
    r.register(Tool(
        "search_hospitals",
        "대구 병원을 조건으로 검색해 **여러 곳을 이름순**으로 돌려준다 (추천·순위 아님). "
        "기본은 외국인환자 유치의료기관 등록 병원만. language를 주면 그 언어로 직원 응대 또는 AI 번역 채팅이 되는 병원만.",
        {"type": "object", "properties": {
            "department": {"type": "string", "description": "한국어 진료과명. 예: 피부과, 성형외과, 치과, 내과, 가정의학과, 정형외과, 한방"},
            "district": {"type": "string", "enum": DISTRICTS},
            "language": {"type": "string", "enum": LANGS, "description": "사용자 언어 코드"},
            "open_on": {"type": "string", "enum": WEEKDAYS, "description": "그 요일에 진료하는 곳만"},
            "registered_only": {"type": "boolean", "description": "기본 true"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
         "required": ["department"]},
        search_hospitals, "병원찾기"))
    r.register(Tool(
        "get_hospital",
        "병원 1곳의 상세 정보(주소·전화·진료시간·지원 언어·상담 요청 가능 여부). 평가 정보는 없다.",
        {"type": "object", "properties": {"hospital_id": {"type": "integer"}}, "required": ["hospital_id"]},
        get_hospital, "병원찾기"))
    r.register(Tool(
        "get_prices",
        "가격·비용·'얼마예요' 질문에는 **항상 이 도구**를 쓴다. 공공 비급여 고지 금액(내국인 기준)을 데이터 그대로 돌려준다. "
        "병원을 몰라도 item만으로 조회 가능. 숫자는 이 결과만 사용하고 직접 만들지 않는다.",
        {"type": "object", "properties": {
            "hospital_id": {"type": "integer"},
            "item": {"type": "string", "description": "시술·항목 키워드 (한국어 또는 영어)"}}},
        get_prices, "가격"))
    r.register(Tool(
        "retrieve_docs",
        "이용 절차·비자·환자 권리·가격 표시 기준 같은 안내 문서를 검색한다 (구체적인 금액은 get_prices). "
        "결과 문서에 있는 내용만 출처·기준일과 함께 답한다.",
        {"type": "object", "properties": {
            "query": {"type": "string"},
            "topic": {"type": "string", "enum": DOC_TOPICS}},
         "required": ["query"]},
        retrieve_docs, "정보질문"))
    r.register(Tool(
        "check_availability",
        "사용자가 고른 병원의 상담 가능 시간 후보를 날짜 범위로 조회한다 (확정 아님).",
        {"type": "object", "properties": {
            "hospital_id": {"type": "integer"},
            "date_from": {"type": "string", "description": "YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD, 없으면 date_from 하루"}},
         "required": ["hospital_id", "date_from"]},
        check_availability, "예약"))
    r.register(Tool(
        "prepare_booking_request",
        "사용자가 **직접 고른** 병원에 보낼 상담 요청서 **초안**을 만든다. 제출은 하지 않는다 — 사용자가 화면의 제출 버튼을 누른다. "
        "빠진 값이 있으면 needs_info를 돌려주므로 사용자에게 물어본다.",
        {"type": "object", "properties": {
            "hospital_id": {"type": "integer"},
            "preferred_slots": {"type": "array", "items": {"type": "string"},
                                "description": "희망 일시 후보, 'YYYY-MM-DD HH:MM'"},
            "language": {"type": "string", "enum": LANGS},
            "inquiry": {"type": "string", "description": "상담하고 싶은 내용 (사용자 표현 그대로)"},
            "needs_interpreter": {"type": "boolean"}},
         "required": ["hospital_id"]},
        prepare_booking_request, "예약"))
    r.register(Tool(
        "get_my_bookings",
        "로그인한 사용자의 상담 요청 목록과 상태(pending/confirmed/rejected/proposed/cancelled/expired)를 조회한다.",
        {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["pending", "confirmed", "rejected", "proposed", "cancelled", "expired"]}}},
        get_my_bookings, "예약상태"))
    r.register(Tool(
        "open_aftercare_thread",
        "방문을 마친 예약에 대해 병원과의 **비의료** 문의 채팅방(일정·비용·서류·숙박)을 연다. 증상·치료 상담에는 쓰지 않는다.",
        {"type": "object", "properties": {
            "booking_id": {"type": "string"},
            "topic": {"type": "string", "enum": AFTERCARE_TOPICS},
            "message": {"type": "string", "description": "병원에 보낼 첫 메시지 (사용자 표현 그대로)"}},
         "required": ["booking_id", "topic", "message"]},
        open_aftercare_thread, "사후문의"))
    return r
