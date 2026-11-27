"""챗봇(오케스트레이터)이 부르는 환자 쪽 도구 13개. 실제 서버는 DB 게이트웨이(ctx.hospitals·ctx.store), 테스트·평가는 가상 데이터(fake_data.py).

| 의도 | 도구 |
|---|---|
| 진료과안내 | suggest_department |
| 병원찾기 | search_hospitals, get_hospital |
| 병원추천 | recommend_hospitals |
| 가격 | get_prices |
| 정보질문 | retrieve_docs |
| 예약 | check_availability, prepare_booking_request, record_residency |
| 예약상태 | get_my_bookings |
| 예약문의 (방문 전) | draft_hospital_question |
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
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from ai.agent.tools import fake_data as fd
from ai.agent.tools.booking_store import (
    BookingError, BookingStore, parse_local_slot, required_consents, to_booking_create,
)
from ai.agent.tools.registry import JSON, Tool, ToolContext, ToolError, ToolRegistry
from ai.llm.safety import _VISA_RE

# 사용자 언어 코드 = 프론트·백엔드가 지원하는 6개 (backend `patients.preferred_lang`, 요청서 `lang`)
LANGS = ["en", "zh-CN", "zh-TW", "vi", "ko", "ja"]
# 한국어 진료과 이름 → DB `departments.code` (= 프론트 키, docs/backend-db-schema.md 5절).
# 표에 없는 진료과(치과·정형외과·한방 등)는 병원 찾기까지만 되고 예약 요청은 못 한다. DB 진료과가 늘면 표만 넓힌다
DEPT_CODES = {"피부과": "dermatology", "성형외과": "plastic", "내과": "internal", "안과": "ophthalmology"}


def lang_family(lang: str) -> str:
    """병원 직원 응대 언어는 중국어를 간체·번체로 나누지 않는다 (`zh`)."""
    return "zh" if lang.startswith("zh") else lang
DISTRICTS = ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"]
# 지역 이름 별칭 (영어·한자 간체·번체·일본어). 모델이 寿城区를 달성군으로 옮긴 사례가 있어 코드에서 바꾼다 (2026-11-26)
DISTRICT_ALIASES = {
    "중구": ["jung-gu", "junggu", "jung", "中区", "中區"],
    "동구": ["dong-gu", "donggu", "东区", "東區", "東区"],
    "서구": ["seo-gu", "seogu", "西区", "西區"],
    "남구": ["nam-gu", "namgu", "南区", "南區"],
    "북구": ["buk-gu", "bukgu", "北区", "北區"],
    "수성구": ["suseong-gu", "suseonggu", "suseong", "寿城区", "壽城區", "寿城區", "壽城区"],
    "달서구": ["dalseo-gu", "dalseogu", "dalseo", "达西区", "達西區", "達西区"],
    "달성군": ["dalseong-gun", "dalseonggun", "dalseong", "达城郡", "達城郡"],
    "군위군": ["gunwi-gun", "gunwigun", "gunwi", "军威郡", "軍威郡"],
}
_DISTRICT_LOOKUP = {a.lower(): ko for ko, names in DISTRICT_ALIASES.items() for a in [ko, *names]}
DISTRICT_HELP = ("대구의 구·군. 한국어 이름으로 넣는다: " + ", ".join(f"{ko}({names[0]}, {names[3] if len(names) > 3 else names[-1]})"
                 for ko, names in DISTRICT_ALIASES.items()) + ". 사용자가 다른 언어로 말해도 위 표로 바꾼다")


def _district(args: JSON) -> JSON:
    """district 별칭(영어·한자)을 한국어 이름으로. 모르는 값이면 다시 고르게 오류."""
    d = args.get("district")
    if not d:
        return args
    key = " ".join(str(d).split()).lower().removeprefix("daegu ").removeprefix("대구 ").removeprefix("대구")
    ko = _DISTRICT_LOOKUP.get(key) or _DISTRICT_LOOKUP.get(key.replace(" ", "-"))
    if ko is None:
        raise ToolError(f"Unknown district '{d}'. Use one of: {', '.join(DISTRICTS)} "
                        "(e.g. 수성구 = Suseong-gu = 寿城区).")
    return {**args, "district": ko}
AFTERCARE_TOPICS = ["schedule", "cost", "documents", "accommodation", "other_non_medical"]
DOC_TOPICS = ["visa", "procedure", "rights", "payment", "other"]

MEDICAL_DISCLAIMER = "General information only. Diagnosis and suitable treatment must be decided by a doctor."
NEUTRAL_NOTE = "Listed in name order. This is not a recommendation or ranking."
LANGUAGE_UNKNOWN_NOTE = ("Language support is not in the hospital data, so the list is not filtered by language. "
                         "Ask the hospital which languages they support.")
RECOMMEND_BASIS = (
    "Suggested only by how well each hospital matches the user's stated conditions (staff language, opening day, "
    "available time). This is not a judgment of medical quality, skill or results. All are registered foreign-patient "
    "facilities. MediDaegu is a registered patient facilitator and may receive a referral fee from hospitals; "
    "the fee does not affect the order."
)
# 가격 가이드 화면(프론트 /prices)의 진료과 키 — 챗봇 가격 버튼이 그 과로 열리게 (2026-11-26)
PRICE_GUIDE_DEPTS = {"피부과": "dermatology", "성형외과": "plastic", "내과": "internal", "안과": "ophthalmology",
                     "한방": "korean_medicine", "한의원": "korean_medicine"}
PRICE_NOTE = "Public non-covered fee notice for Korean patients (demo values). Final cost may differ; ask the hospital."


def _hospital_card(h: dict) -> JSON:
    return {
        "hospital_id": h["id"],
        "name_ko": h["name_ko"],
        "name_en": h["name_en"],
        "district": h["district"],
        "departments": h["departments"],
        "is_registered_facility": h["is_registered_facility"],
        "tel": h["tel"],
        # 번역 가능 병원 표시 (plan 12-1 #5): 직원 직접 응대 언어와 AI 번역 채팅을 구분
        "staff_languages": h["staff_languages"],
        "ai_translation_chat": h["ai_translation_chat"],
    }


def _find_hospital(hospital_id: int) -> dict:
    for h in fd.HOSPITALS:
        if h["id"] == hospital_id:
            return h
    raise ToolError(f"병원 {hospital_id}을(를) 찾을 수 없습니다")


def _uses_db(ctx: ToolContext) -> bool:
    return ctx.hospitals is not None and hasattr(ctx.hospitals, "booking_info")


def _booking_hospital(ctx: ToolContext, hospital_id: int) -> dict:
    """조건 맞춤 제안·예약용 병원. 실제 서버에서는 DB (가상 입점 병원만 요청을 받음, 결정 31), 테스트는 가상 데이터."""
    if _uses_db(ctx):
        h = ctx.hospitals.booking_info(hospital_id)
        if h is None:
            raise ToolError(f"병원 {hospital_id}을(를) 찾을 수 없습니다")
        return h
    return {**_find_hospital(hospital_id), "accepts_requests": True}


WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _slots_from_hours(h: dict, day: date) -> list[str]:
    """진료 시간 안의 정시 후보 (마감 1시간 전까지, 점심 제외). 확정은 병원이 함.
    점심은 병원 자료(lunch)가 있으면 그 시간, 없으면 13시만 뺀다 (예전 기준)."""
    key = WEEKDAYS[day.weekday()]
    span = h.get("hours", {}).get(key)
    if not span:
        return []
    open_, close = span.split("-")
    start = int(open_[:2]) + (0 if open_[3:] == "00" else 1)  # 09:30 시작이면 10시부터
    end = int(close[:2])
    lunch = (h.get("lunch") or {}).get(key) if isinstance(h.get("lunch"), dict) else None
    if lunch:
        l0, l1 = lunch.split("-")
        return [f"{t:02d}:00" for t in range(start, end) if not (l0 <= f"{t:02d}:00" < l1)]
    return [f"{t:02d}:00" for t in range(start, end) if t != 13]


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


RESIDENT_LIST_NOTE = ("This user lives in Korea: consultation requests and suggestions through MediDaegu are not available. "
                      "Do not offer to book or send a request; the user can contact the hospitals directly.")


def search_hospitals(args: JSON, ctx: ToolContext) -> JSON:
    args = _district(args)
    res = _search_hospitals(args, ctx)
    for h in res.get("hospitals", []):
        if "tel" in h:
            h["tel"] = daegu_tel(h["tel"]) or None
    shown = len(res.get("hospitals", []))
    res["shown"] = shown
    if res.get("count", shown) > shown:  # 답의 "5곳"과 카드 "7곳"이 달라 보이던 것 (2026-11-26)
        res["note"] = f"{res['note']} Showing {shown} of {res['count']} hospitals; say both numbers."
    if any(h.get("tel") is None for h in res.get("hospitals", [])):
        res["note"] = (f"{res['note']} Hospitals with no tel are demo hospitals (가상/Demo) for the presentation and have "
                       "no phone number: if you list phone numbers, say so for them instead of leaving it out.")
    if ctx.residency == "resident":  # 목록 끝에 "상담 요청 도와드릴까요?"를 붙이지 않게 (2026-11-26)
        res["note"] = f"{res['note']} {RESIDENT_LIST_NOTE}"
    return res


def _search_hospitals(args: JSON, ctx: ToolContext) -> JSON:
    dept = args["department"]
    if ctx.hospitals is not None:  # 실제 병원 DB
        code = DEPT_CODES.get(dept)
        note = NEUTRAL_NOTE + (" " + LANGUAGE_UNKNOWN_NOTE if args.get("language") else "")
        if code is None:
            return {"count": 0, "hospitals": [], "note": f"{note} The hospital data has only these departments: "
                                                         f"{', '.join(DEPT_CODES)}."}
        found = ctx.hospitals.search(
            dept_code=code, district=args.get("district"), registered_only=args.get("registered_only", True),
            open_on=args.get("open_on"), limit=args.get("limit", 10),
        )
        return {**found, "note": note}
    rows = [h for h in fd.HOSPITALS if dept in h["departments"]]
    if args.get("district"):
        rows = [h for h in rows if h["district"] == args["district"]]
    if args.get("registered_only", True):
        rows = [h for h in rows if h["is_registered_facility"]]
    # 언어는 직원 응대 언어로만 거름 (추천과 같은 기준, AI 번역은 입점 병원 공통이라 기준 아님). 한국어는 거르지 않음
    if (lang := args.get("language")) and lang_family(lang) != "ko":
        rows = [h for h in rows if lang_family(lang) in h["staff_languages"]]
    if day := args.get("open_on"):
        rows = [h for h in rows if h["hours"].get(day)]
    rows.sort(key=lambda h: h["name_en"])  # 중립 정렬
    limit = args.get("limit", 10)
    return {"count": len(rows), "hospitals": [_hospital_card(h) for h in rows[:limit]], "note": NEUTRAL_NOTE}


def recommend_hospitals(args: JSON, ctx: ToolContext) -> JSON:
    args = _district(args)
    # 소개·알선은 건강보험 미가입·국내 비거주 외국인에게만 허용 (의료법 제27조 제3항 제2호, 시행규칙 제19조의2)
    if ctx.residency is None:
        return {"status": "needs_info", "ask": "residency",
                "question": "Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?"}
    if ctx.residency == "resident":
        return {"status": "not_available",
                "reason": "Hospital suggestions are for short-term visitors. Use search_hospitals to show the neutral list instead."}
    dept = args["department"]
    if _uses_db(ctx):  # 실제 서버: 메디대구 입점 가상 병원만 (결정 31)
        code = DEPT_CODES.get(dept)
        rows = ctx.hospitals.demo_candidates(code, args.get("district")) if code else []
    else:
        rows = [h for h in fd.HOSPITALS if dept in h["departments"] and h["is_registered_facility"]]
        if args.get("district"):
            rows = [h for h in rows if h["district"] == args["district"]]
    lang, day, pref = args.get("language"), args.get("open_on"), args.get("preferred_date")
    if pref:
        pref_day = _parse_date(pref, "preferred_date")
    scored = []
    for h in rows:
        score, reasons = 0, []
        # 언어 조건은 직원 응대 언어로만 맞춘다. AI 번역 채팅은 입점 병원 모두 지원하는 플랫폼 기능이라
        # 추천 기준이 되지 않음 (2026-11-26). 한국어는 모든 병원이 되므로 조건에서 뺀다
        if lang and lang_family(lang) != "ko":
            if lang_family(lang) not in h["staff_languages"]:
                continue  # 그 언어를 하는 직원이 없으면 제안하지 않음
            score += 2
            reasons.append(f"staff speak {lang_family(lang)}")
        if day and h["hours"].get(day):
            score += 1
            reasons.append(f"open on {day} ({h['hours'][day]})")
        has_slot = _slots_from_hours(h, pref_day) if pref and _uses_db(ctx) else fd.AVAILABILITY.get(h["id"], {}).get(pref)
        if pref and has_slot:
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
    if ctx.hospitals is not None:  # 실제 병원 DB
        found = ctx.hospitals.get(args["hospital_id"])
        if found is None:
            raise ToolError(f"병원 {args['hospital_id']}을(를) 찾을 수 없습니다")
        return found
    h = _find_hospital(args["hospital_id"])
    return {**_hospital_card(h), "hours": h["hours"], "address_en": h["address_en"], "tel": h["tel"],
            "hours_source": "demo", "can_request_consultation": h["is_registered_facility"]}


def get_prices(args: JSON, ctx: ToolContext) -> JSON:
    if _uses_db(ctx):
        # 챗봇 가격은 아직 실제 데이터에 연결 전. 가짜 행(fake_data.PRICES)은 id가 시연 병원과 겹쳐 엉뚱한 값이 됨 (11/24)
        # 대신 가격 가이드 화면으로 가는 버튼 카드(price_guide): 시술 이름(q)·진료과(dept)로 걸러서 열림 (11/26)
        item = " ".join(str(args.get("item") or "").split())[:40] or None
        return {"prices": [], "guide_link": {"q": item, "dept": PRICE_GUIDE_DEPTS.get(args.get("department") or "")},
                "note": "The chatbot can't look up prices. A button to the Price Guide page"
                        + (f" filtered to '{item}'" if item else "") + " is shown under your reply (in Korean the page is "
                        "'가격 가이드'; use the page name in the user's language). Tell the user to press it to see the price "
                        "ranges listed there for Daegu, that actual costs differ by hospital, and that the hospital gives "
                        "the final estimate. Do not quote any numbers and do not call them official or public prices. "
                        "Answer only the price question; don't add booking questions."}
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
    # 비자는 안내하지 않는다 (2026-11-24 결정) — 비자 문서는 돌려주지 않고 대사관·영사관 안내만
    if topic == "visa" or any(p.search(args["query"]) for p in _VISA_RE):
        return {"documents": [], "note": "Visa questions are not answered here. Say you can't help with visas and ask the "
                                         "user to contact the Korean embassy or consulate in their country."}
    rows = [d for d in fd.DOCS if d["topic"] != "visa" and (topic in (None, "other") or d["topic"] == topic)]
    if topic in (None, "other"):
        rows = [d for d in rows if any(w in (d["title"] + d["text"]).lower() for w in q.split())] or []
    if not rows:
        return {"documents": [], "note": "No document found. Say you don't know; do not answer from memory."}
    return {"documents": rows, "note": "Answer only from these documents and show source and as_of."}


def check_availability(args: JSON, ctx: ToolContext) -> JSON:
    h = _booking_hospital(ctx, args["hospital_id"])
    start = _parse_date(args["date_from"], "date_from")
    end = _parse_date(args.get("date_to") or args["date_from"], "date_to")
    if end < start:
        raise ToolError("date_to가 date_from보다 빠릅니다")
    if _uses_db(ctx):  # 가상 병원 진료 시간에서 정시 후보 (최대 14일)
        days = [start + timedelta(days=i) for i in range(min((end - start).days + 1, 14))]
        slots = {d.isoformat(): t for d in days if (t := _slots_from_hours(h, d))}
    else:
        slots = {d: t for d, t in fd.AVAILABILITY.get(h["id"], {}).items() if start <= date.fromisoformat(d) <= end}
    return {"hospital_id": h["id"], "slots": slots,
            "note": "Times are candidates only. The hospital confirms the booking."}


def prepare_booking_request(args: JSON, ctx: ToolContext) -> JSON:
    if ctx.residency is None:
        return {"status": "needs_info", "ask": "residency",
                "question": "Are you visiting Korea short-term, or do you live in Korea (alien registration / NHIS)?"}
    h = _booking_hospital(ctx, args["hospital_id"])
    if ctx.residency == "resident":
        return {"status": "not_available",
                "reason": "Consultation requests through MediDaegu are for short-term visitors. Please contact the hospital directly.",
                "hospital_tel": daegu_tel(h["tel"])}
    if not h["is_registered_facility"]:
        return {"status": "not_available",
                "reason": "This hospital is not a registered foreign-patient facility, so requests can't be sent here.",
                "hospital_tel": daegu_tel(h["tel"])}
    if not h.get("accepts_requests", True):  # 등록 병원이지만 메디대구 입점 X (결정 31: 예약은 가상 입점 병원만)
        return {"status": "not_available",
                "reason": "This hospital is a registered foreign-patient facility, but it is not a MediDaegu partner hospital, "
                          "so consultation requests can't be sent through us. Don't say it is unregistered. "
                          "Use recommend_hospitals to suggest MediDaegu partner hospitals (demo), or share the hospital's phone.",
                "hospital_tel": daegu_tel(h["tel"])}
    # 백엔드 BookingCreate(docs/backend-contracts.md 6절)가 요구하는 칸. 연락 방법은 계정 이메일로 고정
    department = args.get("department") or (h["departments"][0] if len(h["departments"]) == 1 else None)
    if department and department not in DEPT_CODES:
        return {"status": "not_available",
                "reason": f"Online consultation requests are currently available for {', '.join(DEPT_CODES)} only. "
                          f"Please contact the hospital directly for {department}.",
                "hospital_tel": daegu_tel(h["tel"])}
    # 비자 도움 여부는 사용자가 직접 답한 경우만 받는다 — 모델이 질문을 건너뛰고 False를 지어 넣은 사례 (2026-11-24)
    visa_unconfirmed = args.get("visa_needed") is not None and not _user_said(args.get("visa_statement"), ctx)
    if visa_unconfirmed:
        args = {**args, "visa_needed": None}
    missing = [k for k in ("department", "preferred_slots", "language", "nationality", "visa_needed", "inquiry")
               if (department if k == "department" else args.get(k)) in (None, "", [])]
    if missing:
        out = {"status": "needs_info", "missing": missing, "hospital_departments": h["departments"]}
        if "visa_needed" in missing:
            out["note"] = ("Ask the user whether they want the hospital's help with visa paperwork and wait for their answer. "
                           "Then pass visa_needed with visa_statement copied from their own words. Never assume it.")
        return out
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
        if _uses_db(ctx):  # 진료시간 밖이면 서버가 422로 막으므로 초안 단계에서 미리 알림 (11/24 — 21시 요청)
            # hours: 값 = "HH:MM-HH:MM", None = 휴진, 키 없음 = 모름(막지 않음 — 서버 _check_open과 같은 기준)
            hours = h.get("hours") if isinstance(h.get("hours"), dict) else {}
            day_key = WEEKDAYS[slot.weekday()]
            span = hours.get(day_key)
            hhmm = s.strip()[-5:]
            if day_key in hours and span is None:
                raise ToolError(f"The hospital is closed on that day: {s}. Ask the user for another day "
                                f"(hours: {h['hours']}). Use check_availability for candidate times.")
            if span and not (span.split("-")[0] <= hhmm < span.split("-")[1]):
                raise ToolError(f"{hhmm} is outside the hospital's hours that day ({span}): {s}. Ask the user for a time "
                                "within the hours. Use check_availability for candidate times.")
            # 점심시간 (서버 _check_open과 같은 기준). lunch: 요일 → "HH:MM-HH:MM", 없으면 점심 정보 없음 (11/26)
            lunch = (h.get("lunch") or {}).get(day_key) if isinstance(h.get("lunch"), dict) else None
            if lunch and lunch.split("-")[0] <= hhmm < lunch.split("-")[1]:
                raise ToolError(f"{hhmm} is during the hospital's lunch break that day ({lunch}): {s}. Ask the user for "
                                "another time. Use check_availability for candidate times.")
    # 국적은 초안에 저장돼 매 턴 "신뢰" 맥락에 들어가므로 자유 문장을 받지 않는다 (프롬프트 주입 경로 차단)
    nationality = str(args["nationality"]).strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", nationality):
        raise ToolError("nationality는 ISO 3166-1 alpha-2 국가 코드(예: TW, VN, US)여야 합니다")
    if nationality == "KR":  # 한국 국적은 해외에 살아도 유치 대상 아님 (결정 36, 서버도 403)
        return {"status": "not_available",
                "reason": "Consultation requests through MediDaegu are for foreign short-term visitors. Korean nationals "
                          "(even if living abroad) can't send requests through us. Please contact the hospital directly.",
                "hospital_tel": daegu_tel(h["tel"])}
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


def daegu_tel(tel: str | None) -> str | None:
    """지역번호가 빠진 시내 번호(예: 253-0707)에 대구 053을 붙인다. 병원 목록은 대구만이라 안전.
    0으로 시작(053·010 등)하거나 15xx·16xx·18xx 대표번호는 그대로."""
    if not tel:
        return tel
    digits = re.sub(r"\D", "", tel)
    if tel.startswith("0") or re.fullmatch(r"1[5-8]\d{6}", digits) or len(digits) not in (7, 8):
        return tel
    return f"053-{tel}"


def _user_said(statement: Any, ctx: ToolContext) -> bool:
    """근거 문구가 이 대화의 사용자 메시지 안에 그대로 있는지 (공백·대소문자 무시). user_texts가 None이면 검사 생략."""
    if ctx.user_texts is None:
        return True
    quote = " ".join(str(statement or "").split()).lower()
    if len(quote) < 2:
        return False
    return any(quote in " ".join(t.split()).lower() for t in ctx.user_texts)


def record_residency(args: JSON, ctx: ToolContext) -> JSON:
    # 사용자가 채팅에서 직접 말한 값만 기록 (자기 신고). 실제 서비스에서는 가입 단계 확인 값이 우선.
    # 모델이 추측으로 기록하는 것을 코드로 막는다: 인용문이 이번 사용자 메시지 안에 실제로 있어야 함
    # (2026-11-10 실제 호출에서 사용자가 답하기 전에 short_term으로 기록한 사례 확인)
    if ctx.residency_locked:  # 가입 때 답한 값이 있음 → 바꾸려면 마이페이지에서 다시 답함 (결정 28)
        return {"status": "not_recorded", "residency": ctx.residency,
                "reason": "Residency comes from the user's account answers. To change it, the user updates it in My Page."}
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
    # 실제 저장소(backend BookingGateway)는 병원이 사후관리를 하는지·이미 있는 대화를 알려 줌. 가짜 저장소는 가상 대화
    info = (ctx.store.aftercare_for(ctx.patient_id, bk["id"]) if hasattr(ctx.store, "aftercare_for")
            else {"available": True, "thread_id": f"demo-thread-{bk['id']}"})
    if not info.get("available"):
        return {"status": "not_available", "reason": "This hospital does not take follow-up messages here. "
                "Tell the user to contact the hospital directly."}
    # 메시지는 여기서 보내지 않음: 카드의 버튼으로 사후관리 화면을 열고 사용자가 직접 보냄 (AI가 대신 보내지 않게)
    return {
        "status": "opened", "thread_id": info.get("thread_id") or "", "booking_id": bk["id"],
        "hospital_id": bk["hospital_id"], "topic": args["topic"], "first_message": args["message"],
        "notice": "For schedule, cost, documents or accommodation questions only. This is not medical consultation.",
        "note": "Not sent yet. Tell the user to press the button on the card to open the follow-up chat and send it.",
    }


QUESTION_OPEN = ("pending", "proposed", "confirmed")


def draft_hospital_question(args: JSON, ctx: ToolContext) -> JSON:
    """방문 전 질문 초안 카드 (결정 32). 보내지 않음 — 환자가 카드에서 [보내기] (POST /me/booking-requests/{id}/questions)."""
    if not ctx.patient_id:
        return {"status": "login_required"}
    try:
        bk = _store(ctx).get_for_patient(ctx.patient_id, args["booking_id"])
    except BookingError as e:
        raise ToolError("내 예약에서 해당 booking_id를 찾을 수 없습니다") from e
    if bk.get("visited"):
        return {"status": "not_available", "reason": "The visit is done. Use open_aftercare_thread for follow-up questions."}
    if bk.get("status") not in QUESTION_OPEN:
        return {"status": "not_available", "reason": f"This booking is {bk.get('status')}. Questions can be sent only "
                "before the visit while the booking is pending, proposed or confirmed."}
    draft = " ".join(str(args["draft"]).split())[:1000]
    if not draft:
        raise ToolError("draft가 비어 있습니다")
    return {
        "status": "draft", "booking_id": bk["id"], "hospital_id": bk["hospital_id"],
        "hospital_name_en": bk.get("hospital_name_en"), "draft": draft,
        "notice": "The hospital staff answer this. MediDaegu does not give medical advice.",
        "note": "Not sent yet. Ask the user to check the draft and press Send on the card.",
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
        "기본은 외국인환자 유치의료기관 등록 병원만. language를 주면 그 언어로 응대하는 직원이 있는 병원만 (AI 번역 채팅은 기준 아님).",
        {"type": "object", "properties": {
            "department": {"type": "string", "description": "한국어 진료과명. 예: 피부과, 성형외과, 치과, 내과, 가정의학과, 정형외과, 한방"},
            "district": {"type": "string", "description": DISTRICT_HELP},
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
            "district": {"type": "string", "description": DISTRICT_HELP},
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
            "item": {"type": "string", "description": "시술·항목 키워드, 사용자가 말한 그대로 짧게 (예: 필러, 보톡스, 라식, 건강검진)"},
            "department": {"type": "string", "enum": list(PRICE_GUIDE_DEPTS),
                           "description": "그 시술을 보통 다루는 진료과 (알면). 가격 가이드 버튼이 이 과로 열림"}}},
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
        "빠진 값이 있으면 needs_info의 missing을 돌려주므로 빠진 것을 **한 메시지에 모아** 물어본다. 값은 사용자가 말한 것만 쓰고 추측하지 않는다.",
        {"type": "object", "properties": {
            "hospital_id": {"type": "integer"},
            "department": {"type": "string", "description": "한국어 진료과명. 병원 진료과가 하나면 생략 가능"},
            "preferred_slots": {"type": "array", "items": {"type": "string"},
                                "description": "희망 일시 후보 1~3개, 병원 현지(한국) 시간 'YYYY-MM-DD HH:MM'"},
            "language": {"type": "string", "enum": LANGS},
            "nationality": {"type": "string", "description": "국적 ISO 3166-1 alpha-2 코드 (TW, VN, US, CN, JP, TH ...). 사용자가 말한 국가명을 코드로 바꿔 넣는다"},
            "visa_needed": {"type": "boolean", "description": "병원에서 비자 관련 서류 안내가 필요하다고 사용자가 말했는지. 사용자가 답하기 전에는 넣지 않는다"},
            "visa_statement": {"type": "string",
                               "description": "visa_needed의 근거: 사용자 메시지에서 **그대로 복사한** 답 (번역·요약 X, 예: \"아니요 필요 없어요\"). 없으면 visa_needed도 넣지 않는다"},
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
    r.register(Tool(
        "draft_hospital_question",
        "방문 **전** 예약(대기·제안·확정)에 대해 병원에 보낼 질문 **초안 카드**를 만든다. 보내지 않는다 — 사용자가 카드에서 [보내기]. "
        "의료 판단은 직접 답하지 말고 이 도구로 병원에 묻게 한다.",
        {"type": "object", "properties": {
            "booking_id": {"type": "string", "description": "get_my_bookings의 예약 id"},
            "draft": {"type": "string", "description": "병원에 보낼 질문 초안 (사용자 언어, 짧고 정중하게, 1000자 이내)"}},
         "required": ["booking_id", "draft"]},
        draft_hospital_question, "예약문의"))
    return r
