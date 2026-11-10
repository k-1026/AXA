"""개인정보 마스킹, 의료 판단 거절 규칙, 면책 문구 (docs/compliance.md 기준).

LLM을 부르기 **전에** 코드로 하는 검사 (LLM 호출 없음 → 무료 키 한도와 무관, 결과가 항상 같음).

| 단계 | 무엇 | 결과 |
|---|---|---|
| 1 | 응급 표현 (가슴 통증·호흡 곤란·심한 출혈·의식 저하 — 병명만 말한 경우는 제외) | **block** — LLM 없이 119 안내 고정 문구 |
| 2 | 개인정보 (이메일·전화·여권번호·외국인등록번호) | 마스킹한 글만 LLM에 전달 |
| 3 | 의료 판단 요청 (진단, 효과·부작용, 약·용량), 병원 평판·실력 비교 요청 | **guard** — 막지 않고, 그 부분을 거절하라는 지시를 이번 턴에 덧붙임 + 화면에 의료 고지 |

3번을 통째로 막지 않는 이유: "흉터가 있는데 어디가 제일 좋아요?"처럼 거절할 부분과 도와줄 부분(병원 찾기·예약)이
한 문장에 섞여 온다. 통째로 막으면 원스톱 흐름이 끊긴다 (subject/plan.md 12-5 "증상 → 진료과 → 병원 → 예약").
병원 **추천 요청은 guard 대상이 아니다** (2026-11-10 변경): 메디대구를 등록 유치사업자로 가정하면 단기 방문 외국인에게
병원을 소개·알선하는 것은 허용된 유치 행위다 (의료법 제27조 제3항 제2호, 의료해외진출법 제2조 제3호·제6조 제2항).
의료 판단은 등록과 무관하게 금지 그대로다 (의료법 제27조 제1항 — 의료인이 아니면 의료행위 불가).
근거: research/의료관광/방향성-검토-플랫폼-샌드박스.md 5절.
키워드 목록은 완전하지 않다 → 시스템 프롬프트의 금지 규칙이 기본 방어선, 이 파일은 보강.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ------------------------------------------------------------------ 1. 응급
EMERGENCY_WORDS = [
    # ko
    "가슴 통증", "가슴이 아파", "흉통", "숨이 안", "숨을 못", "숨쉬기 힘", "호흡 곤란", "호흡곤란", "피가 멈추지", "출혈이 심",
    "피가 많이", "의식이 없", "의식을 잃", "쓰러졌", "쓰러져", "경련을 하", "경련이 멈추",
    # en
    "chest pain", "can't breathe", "cannot breathe", "trouble breathing", "difficulty breathing", "short of breath",
    "heavy bleeding", "bleeding heavily", "won't stop bleeding", "unconscious", "passed out", "fainted",
    "having a seizure", "having a stroke", "having a heart attack", "overdosed",
    # zh (간체·번체)
    "胸痛", "呼吸困难", "呼吸困難", "喘不上气", "喘不過氣", "大出血", "流血不止", "昏迷", "晕倒", "暈倒",
    # vi
    "đau ngực", "khó thở", "chảy máu nhiều", "bất tỉnh", "ngất xỉu",
    # ja
    "胸が痛", "息ができ", "息が苦し", "呼吸困難", "大量出血", "意識がな", "意識不明",
    # th
    "เจ็บหน้าอก", "หายใจไม่ออก", "เลือดออกมาก", "หมดสติ",
    # ru
    "боль в груди", "не могу дышать", "трудно дышать", "сильное кровотечение", "без сознания",
]

EMERGENCY_REPLY = {
    "ko": "응급 상황으로 보입니다. 지금 바로 119에 전화하세요. 119는 무료이며 외국어 통역을 연결해 줍니다. 저는 응급 상황을 도울 수 없습니다.",
    "en": "This sounds like an emergency. Call 119 right now. The call is free and an interpreter can be connected. I can't help with emergencies.",
    "zh": "这听起来像是紧急情况。请立即拨打119。电话免费，并可接通翻译。我无法处理紧急情况。",
    "zh-TW": "這聽起來像是緊急情況。請立即撥打119。電話免費，並可接通翻譯。我無法處理緊急情況。",
    "vi": "Đây có vẻ là tình huống khẩn cấp. Hãy gọi 119 ngay. Cuộc gọi miễn phí và có thể được nối với phiên dịch. Tôi không thể hỗ trợ trường hợp khẩn cấp.",
    "ja": "緊急の状況と思われます。今すぐ119に電話してください。通話は無料で、通訳につないでもらえます。私は緊急時の対応はできません。",
    "th": "ดูเหมือนเป็นเหตุฉุกเฉิน โปรดโทร 119 ทันที โทรฟรีและสามารถต่อสายล่ามได้ ฉันไม่สามารถช่วยในกรณีฉุกเฉินได้",
    "ru": "Похоже, это экстренная ситуация. Немедленно позвоните по номеру 119. Звонок бесплатный, вас могут соединить с переводчиком. Я не могу помочь в экстренных случаях.",
}

# ------------------------------------------------------------------ 2. 개인정보
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("arc", re.compile(r"(?<!\d)\d{6}\s?-\s?[1-8]\d{6}(?!\d)")),  # 외국인등록번호·주민등록번호 형식
    ("passport", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,2}\d{7,8}(?![A-Za-z0-9])")),
    # 전화: +로 시작하거나 0으로 시작, 숫자 9~15개 (날짜 2026-12-01·시간 10:00은 2·1로 시작해 해당 없음)
    ("phone", re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s.-]?)?(?:\(?0\d{1,3}\)?[\s.-]?)\d{3,4}[\s.-]?\d{4}(?!\d)")),
    ("phone", re.compile(r"(?<![\w-])\+\d{1,3}(?:[\s.-]?\d{2,4}){2,4}(?!\d)")),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    """개인정보를 [email] 같은 표시로 바꾼다. (바꾼 글, 찾은 종류 목록)"""
    found: list[str] = []
    for kind, pat in _PII_PATTERNS:
        if pat.search(text):
            found.append(kind) if kind not in found else None
            text = pat.sub(f"[{kind}]", text)
    return text, found


# ------------------------------------------------------------------ 3. 의료 판단·병원 평가
GUARD_PATTERNS: dict[str, list[str]] = {
    # 진단·예후: "이거 무슨 병", "암인가요", "나을까요"
    "diagnosis": [
        r"무슨\s*병", r"어떤\s*병", r"진단해", r"암인가", r"(나을|낫)(까요|나요)", r"심각한가",
        r"what (disease|condition) do i have", r"do i have .{0,30}(cancer|disease|infection|tumou?r|syndrome|allergy)", r"is (it|this) (cancer|serious|dangerous|normal)", r"diagnos(e|is) (me|my)",
        r"will (it|i) (heal|recover|get better)",
        r"是什么病", r"是什麼病", r"严重吗", r"嚴重嗎", r"能治好吗", r"能治好嗎", r"bệnh gì", r"có nghiêm trọng", r"何の病気", r"治りますか",
    ],
    # 시술 적합성·효과·부작용·안전성
    "treatment_judgment": [
        r"효과(가|는)?\s*(있|좋|어때|얼마)", r"부작용", r"안전한가", r"괜찮을까", r"받아도\s*(되|될)", r"(어떤|무슨)\s*시술(이|을)?\s*(좋|받|맞)",
        r"side effects?", r"\bis\b.{0,40}\bsafe\b.{0,15}\bfor (me|my|someone|people|pregnan)", r"\b(laser|treatment|procedure|surgery|botox|filler|injection|medicine|drug|peel|implant)s?\b.{0,25}\bsafe\b", r"\bis (it|this|that) safe (to (get|have|do|take|use|undergo)|after|during)", r"does (it|this) work", r"(treatment|laser|procedure|surgery|botox|filler|injection)s?\b.{0,30}\bworks?\b", r"how effective", r"(which|what) (treatment|procedure|laser) (is|should|would|do)",
        r"should i (get|have|do|try) .{0,40}(surgery|laser|botox|filler|treatment|procedure|implant|injection|lift|peel)", r"is .{0,40}(right|suitable|good) for me",
        r"副作用", r"效果(好|怎么样|怎麼樣|如何)", r"安全吗", r"安全嗎", r"适合我", r"適合我", r"tác dụng phụ", r"có hiệu quả", r"có an toàn", r"効果(は|が)", r"安全ですか",
    ],
    # 약·용량
    "medication": [
        r"(약|연고).{0,10}(먹어도|발라도|써도|복용)", r"(약|복용)\s*용량", r"처방해",
        r"(can|should) i take .{0,40}(medicine|medication|pills?|drugs?|ibuprofen|aspirin|antibiotics?|painkillers?|tylenol)", r"\bdosage\b", r"\bdose\b", r"prescribe", r"what (medicine|medication|drug)",
        r"吃什么药", r"吃什麼藥", r"剂量", r"劑量", r"liều", r"uống thuốc gì", r"何の薬", r"用量",
    ],
    # 병원 평판·후기·실력 비교 (추천 요청 자체는 해당 없음 → recommend_hospitals 도구로 처리)
    "hospital_evaluation": [
        r"(병원|의원|의사|선생님|여기|거기).{0,10}(어때|괜찮(아|나|은가|을까)|믿을)", r"후기", r"평판", r"보다\s*(더\s*)?(잘|낫|나아|좋)",
        r"(clinic|hospital|doctor)\b.{0,15}\b(any good|reliable|trustworthy|good\?)",
        r"reviews? (of|for|on|about) .{0,30}(clinic|hospital|doctor)", r"(clinic|hospital|doctor)s?\b.{0,20}\breviews?\b", r"\breputation\b",
        r"\bbetter than\b", r"more skilled",
        r"口碑", r"评价", r"評價", r"比.{0,12}(好|强|強)", r"đánh giá", r"tốt hơn", r"口コミ", r"評判", r"より(上手|いい|良い)",
    ],
}
_GUARD_RE = {cat: [re.compile(p, re.IGNORECASE) for p in pats] for cat, pats in GUARD_PATTERNS.items()}

GUARD_NOTES = {
    "diagnosis": "The user is asking for a diagnosis or prognosis. Do not answer that part: say a doctor decides it at the consultation.",
    "treatment_judgment": "The user is asking whether a treatment works, is safe, has side effects, or suits them. "
    "Do not answer that part: say a doctor explains this at the consultation.",
    "medication": "The user is asking about medicine or dosage. Do not answer that part: say a doctor or pharmacist must advise.",
    "hospital_evaluation": "The user is asking for an opinion, review, reputation or skill comparison of hospitals or doctors. "
    "Do not give opinions, reviews or quality comparisons, and do not criticise any hospital. You may state facts from tools "
    "(languages, hours, registration, prices) and, if they want a suggestion, use recommend_hospitals.",
}
GUARD_SUFFIX = " Then help with whatever else they asked that you are allowed to do (department info, hospital search or suggestion, prices, booking)."


# ------------------------------------------------------------------ 결과
@dataclass
class SafetyResult:
    action: str  # "pass" | "guard" | "block"
    text: str  # LLM에 넘길 글 (개인정보 마스킹됨)
    categories: list[str]  # "emergency" 또는 GUARD_PATTERNS의 키들
    reply: str | None = None  # block일 때 고정 답
    note: str | None = None  # guard일 때 이번 턴에만 덧붙일 지시
    pii: list[str] | None = None  # 마스킹한 개인정보 종류


def check(text: str, language: str = "en") -> SafetyResult:
    low = text.lower()
    if any(w.lower() in low for w in EMERGENCY_WORDS):
        reply = EMERGENCY_REPLY.get(language, EMERGENCY_REPLY["en"])
        if language not in ("en", "ko"):
            reply = f"{reply}\n{EMERGENCY_REPLY['en']}"  # 언어 설정이 틀렸을 때를 대비해 영어도 함께
        return SafetyResult("block", text, ["emergency"], reply=reply)

    masked, pii = mask_pii(text)
    cats = [cat for cat, pats in _GUARD_RE.items() if any(p.search(masked) for p in pats)]
    if cats:
        note = " ".join(GUARD_NOTES[c] for c in cats) + GUARD_SUFFIX
        return SafetyResult("guard", masked, cats, note=note, pii=pii)
    return SafetyResult("pass", masked, [], pii=pii)
