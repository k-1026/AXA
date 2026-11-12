"""챗봇(오케스트레이터)이 부르는 환자 쪽 도구 11개 — 지금은 가짜 응답 (fake_data.py).

| 의도 | 도구 |
|---|---|
| 진료과안내 | suggest_department |
| 병원찾기 | search_hospitals, get_hospital |
| 병원추천 | recommend_hospitals |
| 가격 | get_prices |
| 정보질문 | retrieve_docs |
| 예약 | check_availability, prepare_booking_request, record_residency |
| 예약상태 | get_my_bookings |
| 사후문의 | open_aftercare_thread |

규칙 (docs/agent-spec.md, subject/plan.md 12절)
- search_hospitals는 **여러 곳을 이름순(중립)** 으로
- recommend_hospitals는 **조건에 얼마나 맞는지**(언어·요일·희망 날짜)로 최대 3곳을 이유와 함께 제안한다 (2026-11-10 추가).
  등록 유치사업자 가정에서 허용되는 유치 행위. 의료 수준·실력·결과에 대한 평가는 아님. 단기 방문 외국인에게만,
  등록 유치의료기관만, 수수료 관계 고지 포함. 국내 거주자에게는 추천하지 않고 중립 목록으로 안내
- prepare_booking_request는 **초안 카드만** 만든다. 제출은 환자가 화면 버튼으로 (도구로 제출 X)
- 국내 거주 외국인(resident)은 상담 예약 연결 불가 → 병원 연락처만 안내
- 사후 문의는 비의료 주제만 (의료 상담은 2027-05-27 외국인환자 비대면진료 시행 후 확장)
- 진료과 안내는 일반 정보 + "진단은 의료진 확인" 고지
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timezone

from ai.agent.tools import fake_data as fd
from ai.agent.tools.booking_store import (
    BookingError, BookingStore, parse_local_slot, required_consents, to_booking_create,
)
from ai.agent.tools.registry import JSON, Tool, ToolContext, ToolError, ToolRegistry

# 사용자 언어 코드 = 프론트·백엔드가 지원하는 5개 (backend `patients.preferred_lang`, 요청서 `lang`)
LANGS = ["en", "zh-CN", "zh-TW", "vi", "ko"]
# 한국어 진료과 이름 → DB `departments.code` (= 프론트 키, docs/backend-db-schema.md 5절).
# 표에 없는 진료과(치과·정형외과·한방 등)는 병원 찾기까지만 되고 예약 요청은 못 한다. DB 진료과가 늘면 표만 넓힌다
DEPT_CODES = {"피부과": "dermatology", "성형외과": "plastic", "내과": "internal", "안과": "ophthalmology"}


def lang_family(lang: str) -> str:
    """병원 직원 응대 언어는 중국어를 간체·번체로 나누지 않는다 (`zh`)."""
    return "zh" if lang.startswith("zh") else lang
DISTRICTS = ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
AFTERCARE_TOPICS = ["schedule", "cost", "documents", "accommodation", "other_non_medical"]
DOC_TOPICS = ["visa", "procedure", "rights", "payment", "other"]

MEDICAL_DISCLAIMER = "General information only. Diagnosis and suitable treatment must be decided by a doctor."
NEUTRAL_NOTE = "Listed in name order. This is not a recommendation or ranking."
RECOMMEND_BASIS = (
    "Suggested only by how well each hospital matches the user's stated conditions (language support, opening day, "
    "available time). This is not a judgment of medical quality, skill or results. All are registered foreign-patient "
    "facilities. MediDaegu is a registered patient facilitator and may receive a referral fee from hospitals; "
    "the fee does not affect the order."
)
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
        rows = [h for h in rows if lang_family(lang) in h["staff_languages"] or h["ai_translation_chat"]]
    if day := args.get("open_on"):
        rows = [h for h in rows if h["hours"].get(day)]
    rows.sort(key=lambda h: h["name_en"])  # 중립 정렬
    limit = args.get("limit", 5)
    return {"count": len(rows), "hospitals": [_hospital_card(h) for h in rows[:limit]], "note": NEUTRAL_NOTE}


def recommend_hospitals(args: JSON, ctx: ToolContext) -> JSON:
    # 소개·알선은 건강보험 미가입·국내 비거주 외국인에게만 허용 (의료법 제27조 제3항 제2호, 시행규칙 제19조의2)
    if ctx.residency is None:
        return {"status": "needs_info", "ask": "residency",
                "question": "Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?"}
    if ctx.residency == "resident":
        return {"status": "not_available",
                "reason": "Hospital suggestions are for short-term visitors. Use search_hospitals to show the neutral list instead."}
    dept = args["department"]
    rows = [h for h in fd.HOSPITALS if dept in h["departments"] and h["is_registered_facility"]]
    if args.get("district"):
        rows = [h for h in rows if h["district"] == args["district"]]
    lang, day, pref = args.get("language"), args.get("open_on"), args.get("preferred_date")
    if pref:
        _parse_date(pref, "preferred_date")
    scored = []
    for h in rows:
        score, reasons = 0, []
        if lang:
            if lang_family(lang) in h["staff_languages"]:
                score += 2
                reasons.append(f"staff speak {lang_family(lang)}")
            elif h["ai_translation_chat"]:
                score += 1
                reasons.append("AI translation chat available")
            else:
                continue  # 소통 수단이 없는 병원은 제안하지 않음
        if day and h["hours"].get(day):
            score += 1
            reasons.append(f"open on {day} ({h['hours'][day]})")
        if pref and fd.AVAILABILITY.get(h["id"], {}).get(pref):
            score += 1
            reasons.append(f"consultation slots on {pref}")
        if args.get("district"):
            reasons.append(f"in {h['district']}")
        scored.append((score, h, reasons))
    scored.sort(key=lambda x: (-x[0], x[1]["name_en"]))
    return {
        "status": "ok",
        "count": len(scored),
        "suggestions": [{**_hospital_card(h), "match_reasons": reasons} for _, h, reasons in scored[:3]],
        "basis": RECOMMEND_BASIS,
    }


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
    # 백엔드 BookingCreate(docs/backend-contracts.md 6절)가 요구하는 칸. 연락 방법은 계정 이메일로 고정
    department = args.get("department") or (h["departments"][0] if len(h["departments"]) == 1 else None)
    if department and department not in DEPT_CODES:
        return {"status": "not_available",
                "reason": f"Online consultation requests are currently available for {', '.join(DEPT_CODES)} only. "
                          f"Please contact the hospital directly for {department}.",
                "hospital_tel": h["tel"]}
    missing = [k for k in ("department", "preferred_slots", "language", "nationality", "visa_needed", "inquiry")
               if (department if k == "department" else args.get(k)) in (None, "", [])]
    if missing:
        return {"status": "needs_info", "missing": missing, "hospital_departments": h["departments"]}
    if department not in h["departments"]:
        raise ToolError(f"이 병원의 진료과가 아닙니다: {department} (가능: {h['departments']})")
    slots = args["preferred_slots"]
    if not 1 <= len(slots) <= 3:
        raise ToolError("preferred_slots는 1~3개여야 합니다")
    # 제출 때 백엔드와 같은 기준(오늘 0시 UTC)으로 지난 일시를 미리 거른다 → 제출 단계 422를 줄임
    now = datetime.combine(ctx.today, time(), tzinfo=timezone.utc) if ctx.today else None
    for s in slots:
        try:
            slot = parse_local_slot(s)
        except ValueError as e:
            raise ToolError(f"희망 일시는 'YYYY-MM-DD HH:MM' 형식이어야 합니다: {s}") from e
        if now and slot <= now:
            raise ToolError(f"이미 지난 일시입니다: {s} (오늘 {ctx.today.isoformat()})")
    # 국적은 초안에 저장돼 매 턴 "신뢰" 맥락에 들어가므로 자유 문장을 받지 않는다 (프롬프트 주입 경로 차단)
    nationality = str(args["nationality"]).strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", nationality):
        raise ToolError("nationality는 ISO 3166-1 alpha-2 국가 코드(예: TW, VN, US)여야 합니다")
    draft = {
        "hospital_id": h["id"], "hospital_name_en": h["name_en"], "department": department,
        "department_code": DEPT_CODES[department], "preferred_slots": slots, "language": args["language"], "nationality": nationality,
        "visa_needed": args["visa_needed"], "contact_method": "email", "inquiry": args["inquiry"],
        "needs_interpreter": args.get("needs_interpreter", False),
    }
    if args.get("health_info"):
        draft["health_info"] = args["health_info"]
    return {
        "status": "draft",  # 아직 제출 아님
        "requires_patient_confirmation": True,  # 화면의 [제출] 버튼을 환자가 눌러야 pending 생성
        "draft": draft,
        # 사람이 쓰는 요청서와 **같은 API**로 보낼 값 (결정 3): POST /hospitals/{hospital_id}/booking-requests
        # 본문 = request + 환자가 체크한 consents. 프론트는 변환 없이 그대로 보낸다
        "hospital_id": h["id"],
        "request": to_booking_create(draft, ctx.timezone),
        "consents_required": required_consents(draft),  # 요청서마다 받음. 건강정보는 별도 동의 (개인정보보호법 제23조)
        "note": "Show the summary card. Do not say the request was sent until the user presses Submit.",
    }


def record_residency(args: JSON, ctx: ToolContext) -> JSON:
    # 사용자가 채팅에서 직접 말한 값만 기록 (자기 신고). 실제 서비스에서는 가입 단계 확인 값이 우선.
    # 모델이 추측으로 기록하는 것을 코드로 막는다: 인용문이 이번 사용자 메시지 안에 실제로 있어야 함
    # (2026-11-10 실제 호출에서 사용자가 답하기 전에 short_term으로 기록한 사례 확인)
    quote = " ".join(args["user_statement"].split()).lower()
    said = " ".join(ctx.last_user_text.split()).lower()
    if len(quote) < 3 or quote not in said:
        return {"status": "not_recorded",
                "reason": "The user has not stated this in their latest message. Ask the user and wait for their answer."}
    ctx.residency = args["residency"]
    return {"status": "recorded", "residency": ctx.residency}


def _store(ctx: ToolContext) -> BookingStore:
    if ctx.store is None:
        ctx.store = BookingStore()
    return ctx.store


def get_my_bookings(args: JSON, ctx: ToolContext) -> JSON:
    if not ctx.patient_id:
        return {"status": "login_required"}
    rows = _store(ctx).list_for_patient(ctx.patient_id, args.get("status"))
    # 요청서 원문(request)·동의·이벤트는 모델에 보내지 않는다 (필요한 상태 정보만)
    keep = ("id", "hospital_id", "hospital_name_en", "status", "preferred", "confirmed_slot", "proposed_slot", "created_at", "visited")
    return {"bookings": [{k: b[k] for k in keep if k in b} for b in rows]}


def open_aftercare_thread(args: JSON, ctx: ToolContext) -> JSON:
    if not ctx.patient_id:
        return {"status": "login_required"}
    try:
        bk = _store(ctx).get_for_patient(ctx.patient_id, args["booking_id"])
    except BookingError as e:
        raise ToolError("내 예약에서 해당 booking_id를 찾을 수 없습니다") from e
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
        "대구 병원을 조건으로 검색해 **여러 곳을 이름순**으로 돌려준다 (추천·순위 아님 — 추천 요청은 recommend_hospitals). "
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
        "recommend_hospitals",
        "사용자가 **추천·제안을 요청했을 때** 조건(언어·요일·희망 날짜·지역)에 가장 잘 맞는 등록 병원을 최대 3곳, 이유와 함께 제안한다. "
        "이유는 결과의 match_reasons만 사용한다. 의료 수준·실력·결과 평가가 아니며 '최고'라고 말하지 않는다. "
        "체류 형태를 모르면 needs_info를 돌려주므로 사용자에게 묻는다.",
        {"type": "object", "properties": {
            "department": {"type": "string", "description": "한국어 진료과명. 예: 피부과, 성형외과, 치과, 내과, 가정의학과, 정형외과, 한방"},
            "district": {"type": "string", "enum": DISTRICTS},
            "language": {"type": "string", "enum": LANGS, "description": "사용자 언어 코드"},
            "open_on": {"type": "string", "enum": WEEKDAYS},
            "preferred_date": {"type": "string", "description": "YYYY-MM-DD"}},
         "required": ["department"]},
        recommend_hospitals, "병원추천"))
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
        "빠진 값이 있으면 needs_info의 missing을 돌려주므로 사용자에게 한 번에 하나씩 물어본다. 값은 사용자가 말한 것만 쓰고 추측하지 않는다.",
        {"type": "object", "properties": {
            "hospital_id": {"type": "integer"},
            "department": {"type": "string", "description": "한국어 진료과명. 병원 진료과가 하나면 생략 가능"},
            "preferred_slots": {"type": "array", "items": {"type": "string"},
                                "description": "희망 일시 후보 1~3개, 병원 현지(한국) 시간 'YYYY-MM-DD HH:MM'"},
            "language": {"type": "string", "enum": LANGS},
            "nationality": {"type": "string", "description": "국적 ISO 3166-1 alpha-2 코드 (TW, VN, US, CN, JP, TH ...). 사용자가 말한 국가명을 코드로 바꿔 넣는다"},
            "visa_needed": {"type": "boolean", "description": "병원에서 비자 관련 서류 안내가 필요하다고 사용자가 말했는지"},
            "inquiry": {"type": "string", "description": "상담하고 싶은 내용 (사용자 표현 그대로)"},
            "health_info": {"type": "string", "description": "사용자가 **스스로 말한** 증상·병력 원문. 먼저 묻지 않는다. 없으면 생략"},
            "needs_interpreter": {"type": "boolean"}},
         "required": ["hospital_id"]},
        prepare_booking_request, "예약"))
    r.register(Tool(
        "record_residency",
        "사용자가 **직접 말한** 체류 형태를 기록한다. short_term = 한국에 살지 않는 단기 방문, "
        "resident = 한국 거주(외국인등록·국내거소신고·건강보험 가입). 추측으로 부르지 않는다.",
        {"type": "object", "properties": {
            "residency": {"type": "string", "enum": ["short_term", "resident"]},
            "user_statement": {"type": "string",
                               "description": "사용자의 **이번 메시지에서 그대로 복사한** 근거 문구 (번역·요약 X). 없으면 이 도구를 부르지 말고 사용자에게 묻는다"}},
         "required": ["residency", "user_statement"]},
        record_residency, "예약"))
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
