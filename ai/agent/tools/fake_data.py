"""가짜 응답용 **가상** 데이터. 실제 병원·환자·가격이 아님 (is_demo).

실제 DB·API가 연결되면 chat_tools.py의 핸들러가 이 파일 대신 backend 함수를 부른다.
가격 숫자도 가상 값이다 (발표·시연에서 실제 가격처럼 쓰지 않음).
"""

from __future__ import annotations

# 진료과 일반 안내표 — "보통 어느 과에서 다루는지"만. 진단·적합 시술 판단 X (subject/plan.md 12-5)
DEPARTMENT_GUIDE: list[dict] = [
    {"keywords": ["흉터", "여드름", "acne", "scar", "피부", "skin", "기미", "점", "mole", "痘", "疤", "sẹo", "mụn"],
     "departments": ["피부과", "성형외과"]},
    {"keywords": ["쌍꺼풀", "코", "eyelid", "nose", "rhinoplasty", "双眼皮", "鼻", "mũi", "mắt"],
     "departments": ["성형외과"]},
    {"keywords": ["치아", "임플란트", "teeth", "tooth", "implant", "dental", "牙", "răng"],
     "departments": ["치과"]},
    {"keywords": ["검진", "건강검진", "checkup", "check-up", "health screening", "体检", "khám sức khỏe"],
     "departments": ["가정의학과", "내과"]},
    {"keywords": ["허리", "무릎", "관절", "back", "knee", "joint", "腰", "膝", "đầu gối", "lưng"],
     "departments": ["정형외과", "재활의학과"]},
    {"keywords": ["침", "한방", "acupuncture", "korean medicine", "针灸", "châm cứu"],
     "departments": ["한방"]},
]

HOSPITALS: list[dict] = [
    {"id": 9001, "name_ko": "가상피부과의원 A", "name_en": "Demo Dermatology Clinic A", "district": "수성구",
     "departments": ["피부과"], "type": "의원", "is_registered_facility": True,
     "staff_languages": ["en"], "ai_translation_chat": True,
     "hours": {"mon": "09:30-18:30", "tue": "09:30-18:30", "wed": "09:30-18:30", "thu": "09:30-20:00",
               "fri": "09:30-18:30", "sat": "09:30-14:00", "sun": None},
     "address_en": "Demo-ro 1, Suseong-gu, Daegu", "tel": "053-000-0001"},
    {"id": 9002, "name_ko": "가상피부과의원 B", "name_en": "Demo Dermatology Clinic B", "district": "수성구",
     "departments": ["피부과"], "type": "의원", "is_registered_facility": True,
     "staff_languages": ["en", "zh"], "ai_translation_chat": True,
     "hours": {"mon": "10:00-19:00", "tue": "10:00-19:00", "wed": None, "thu": "10:00-19:00",
               "fri": "10:00-19:00", "sat": "10:00-15:00", "sun": None},
     "address_en": "Demo-ro 2, Suseong-gu, Daegu", "tel": "053-000-0002"},
    {"id": 9003, "name_ko": "가상성형외과의원", "name_en": "Demo Plastic Surgery Clinic", "district": "중구",
     "departments": ["성형외과"], "type": "의원", "is_registered_facility": True,
     "staff_languages": ["zh", "vi"], "ai_translation_chat": False,
     "hours": {"mon": "10:00-19:00", "tue": "10:00-19:00", "wed": "10:00-19:00", "thu": "10:00-19:00",
               "fri": "10:00-19:00", "sat": "10:00-16:00", "sun": None},
     "address_en": "Demo-gil 3, Jung-gu, Daegu", "tel": "053-000-0003"},
    {"id": 9004, "name_ko": "가상치과의원", "name_en": "Demo Dental Clinic", "district": "중구",
     "departments": ["치과"], "type": "의원", "is_registered_facility": True,
     "staff_languages": [], "ai_translation_chat": True,
     "hours": {"mon": "09:00-18:00", "tue": "09:00-18:00", "wed": "09:00-18:00", "thu": "09:00-18:00",
               "fri": "09:00-18:00", "sat": None, "sun": None},
     "address_en": "Demo-gil 4, Jung-gu, Daegu", "tel": "053-000-0004"},
    {"id": 9005, "name_ko": "가상종합검진센터", "name_en": "Demo Health Screening Center", "district": "달서구",
     "departments": ["가정의학과", "내과"], "type": "병원", "is_registered_facility": True,
     "staff_languages": ["en", "ru"], "ai_translation_chat": True,
     "hours": {"mon": "08:00-17:00", "tue": "08:00-17:00", "wed": "08:00-17:00", "thu": "08:00-17:00",
               "fri": "08:00-17:00", "sat": "08:00-12:00", "sun": None},
     "address_en": "Demo-daero 5, Dalseo-gu, Daegu", "tel": "053-000-0005"},
    {"id": 9006, "name_ko": "가상피부과의원 C (미등록)", "name_en": "Demo Dermatology Clinic C", "district": "수성구",
     "departments": ["피부과"], "type": "의원", "is_registered_facility": False,
     "staff_languages": [], "ai_translation_chat": False,
     "hours": {"mon": "09:00-18:00", "tue": "09:00-18:00", "wed": "09:00-18:00", "thu": "09:00-18:00",
               "fri": "09:00-18:00", "sat": None, "sun": None},
     "address_en": "Demo-ro 6, Suseong-gu, Daegu", "tel": "053-000-0006"},
]

# 공공 비급여 고지 금액 형식의 **가상** 값 (원). 실제 심평원 값 아님
PRICES: list[dict] = [
    {"hospital_id": 9001, "item": "흉터 레이저 (1회)", "item_en": "Scar laser (1 session)", "min": 150000, "max": 250000},
    {"hospital_id": 9002, "item": "흉터 레이저 (1회)", "item_en": "Scar laser (1 session)", "min": 120000, "max": 200000},
    {"hospital_id": 9004, "item": "임플란트 (1개)", "item_en": "Dental implant (1 tooth)", "min": 1000000, "max": 1400000},
    {"hospital_id": 9005, "item": "기본 건강검진", "item_en": "Basic health screening", "min": 300000, "max": 300000},
]

DOCS: list[dict] = [
    {"topic": "visa", "title": "Medical tourism visa (C-3-3) overview (demo summary)",
     "text": "Patients staying up to 90 days for treatment may apply for a C-3-3 medical tourism visa. "
             "Required documents are set by the Korean mission; check the official notice before applying.",
     "source": "가상 요약 — 실제 연결 시 하이코리아·재외공관 공지로 교체", "as_of": "2026-11-09"},
    {"topic": "procedure", "title": "How a consultation request works on MediDaegu (demo)",
     "text": "You choose a hospital, send a consultation request, and the hospital confirms, declines or proposes another time. "
             "Treatment contracts and estimated costs are explained by the hospital.",
     "source": "메디대구 이용 안내 (가상)", "as_of": "2026-11-09"},
    {"topic": "rights", "title": "Your rights as a foreign patient (demo)",
     "text": "Registered hospitals must explain the diagnosis, treatment plan and estimated cost. "
             "You may request a written treatment contract and information on dispute resolution.",
     "source": "가상 요약 — 실제 연결 시 의료해외진출법 제8조 원문 기반 문서로 교체", "as_of": "2026-11-09"},
    {"topic": "payment", "title": "Prices shown on MediDaegu (demo)",
     "text": "Prices are public non-covered fee notices for Korean patients and may differ for foreign patients. "
             "Ask the hospital for the final estimate.",
     "source": "메디대구 가격 안내 (가상)", "as_of": "2026-11-09"},
]

# 예약 가능 시간 (가상). 병원 id → 날짜 → 시간 목록
AVAILABILITY: dict[int, dict[str, list[str]]] = {
    9001: {"2026-12-01": ["10:00", "14:00"], "2026-12-02": ["11:00"], "2026-12-03": ["15:30", "17:00"]},
    9002: {"2026-12-01": ["13:00"], "2026-12-04": ["10:00", "16:00"]},
    9003: {"2026-12-02": ["10:00", "14:00"]},
    9004: {"2026-12-01": ["09:30"], "2026-12-03": ["14:00"]},
    9005: {"2026-12-01": ["08:30", "09:00"], "2026-12-02": ["08:30"]},
}

# 환자별 예약 요청 (가상). 상태 코드는 docs/backend-contracts.md 2절
BOOKINGS: list[dict] = [
    {"id": "demo-bk-001", "patient_id": "demo-patient-1", "hospital_id": 9001, "status": "pending",
     "preferred": ["2026-12-01 10:00"], "created_at": "2026-11-08"},
    {"id": "demo-bk-002", "patient_id": "demo-patient-1", "hospital_id": 9005, "status": "confirmed",
     "preferred": ["2026-11-20 08:30"], "confirmed_slot": "2026-11-20 08:30", "created_at": "2026-11-01",
     "visited": True},
]
