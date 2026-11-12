"""챗봇 API 응답 모델 (Pydantic). 백엔드 라우터의 `response_model`이 되고, OpenAPI → `packages/shared-types`로
프론트 타입이 된다. **카드 형식의 기준은 이 파일**이다 (docs/plan-step7-chat-api.md).

카드는 `{"type": ..., "data": {...}}`. 도구 결과(dict)에서 코드가 만들며 LLM이 숫자·병원 정보를 다시 쓰지 않는다.
알 수 없는 칸은 버린다(extra="ignore") — 도구가 칸을 더해도 프론트 계약이 갑자기 바뀌지 않게.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

UI_LANGUAGES = ("ko", "en", "zh-TW", "zh-CN", "vi")  # 백엔드 patients.preferred_lang · 프론트 번역 파일과 같음
Language = Literal["ko", "en", "zh-TW", "zh-CN", "vi"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ------------------------------------------------------------------ 카드 데이터
class HospitalBrief(_Model):
    hospital_id: int
    name_ko: str
    name_en: str
    district: str
    departments: list[str]
    is_registered_facility: bool
    staff_languages: list[str]  # 직원이 직접 응대하는 언어
    ai_translation_chat: bool  # 플랫폼 AI 번역 채팅 지원 (staff_languages와 다른 것)


class HospitalSuggestion(HospitalBrief):
    match_reasons: list[str]  # 조건과 맞는 이유만 (의료 수준 평가 아님)


class HospitalListData(_Model):
    count: int
    hospitals: list[HospitalBrief]
    note: str  # "이름순, 추천·순위 아님"


class HospitalSuggestionsData(_Model):
    count: int
    suggestions: list[HospitalSuggestion]
    basis: str  # 추천 기준 + 수수료 관계 고지


class HospitalDetailData(HospitalBrief):
    hours: dict[str, str | None]  # mon..sun → "09:30-18:30" 또는 휴진(None)
    address_en: str
    tel: str
    hours_source: str
    can_request_consultation: bool


class PriceItem(_Model):
    hospital_id: int
    item: str
    item_en: str
    min: int
    max: int
    currency: str


class PriceListData(_Model):
    prices: list[PriceItem]
    note: str  # "내국인 고지 기준, 최종 금액은 병원 확인"


class SourceDoc(_Model):
    topic: str
    title: str
    text: str
    source: str
    as_of: str


class SourcesData(_Model):
    documents: list[SourceDoc]
    note: str


class TimeSlotsData(_Model):
    hospital_id: int
    slots: dict[str, list[str]]  # 날짜 → 시간 후보 (병원 현지 시간, 확정 아님)
    note: str


class BookingDraftData(_Model):
    """요청서 카드. 프론트의 [제출] = `POST /hospitals/{hospital_id}/booking-requests` 에
    `request` + 환자가 체크한 `consents`([{kind, version}])를 **그대로** 보내기 (사람이 쓰는 요청서와 같은 API)."""

    status: Literal["draft"]
    requires_patient_confirmation: bool
    hospital_id: int
    draft: dict[str, Any]  # 화면 표시용 요약 (병원 이름, 진료과, 희망 일시 등)
    request: dict[str, Any]  # BookingCreate 모양, 희망 일시는 UTC (docs/backend-contracts.md 6절)
    consents_required: list[str]  # privacy / health / overseas_transfer — 체크박스로 보여 줄 목록
    note: str


class BookingBrief(_Model):
    id: str
    hospital_id: int
    hospital_name_en: str | None = None
    status: Literal["pending", "confirmed", "rejected", "proposed", "cancelled", "expired"]
    preferred: list[str] = []
    confirmed_slot: str | None = None
    proposed_slot: str | None = None
    created_at: str | None = None
    visited: bool | None = None


class BookingListData(_Model):
    bookings: list[BookingBrief]


class AftercareThreadData(_Model):
    status: Literal["opened"]
    thread_id: str
    hospital_id: int
    topic: str
    first_message: str
    notice: str


# ------------------------------------------------------------------ 카드 (type으로 구분)
class HospitalListCard(_Model):
    type: Literal["hospital_list"]
    data: HospitalListData


class HospitalSuggestionsCard(_Model):
    type: Literal["hospital_suggestions"]
    data: HospitalSuggestionsData


class HospitalDetailCard(_Model):
    type: Literal["hospital_detail"]
    data: HospitalDetailData


class PriceListCard(_Model):
    type: Literal["price_list"]
    data: PriceListData


class SourcesCard(_Model):
    type: Literal["sources"]
    data: SourcesData


class TimeSlotsCard(_Model):
    type: Literal["time_slots"]
    data: TimeSlotsData


class BookingDraftCard(_Model):
    type: Literal["booking_draft"]
    data: BookingDraftData


class BookingListCard(_Model):
    type: Literal["booking_list"]
    data: BookingListData


class AftercareThreadCard(_Model):
    type: Literal["aftercare_thread"]
    data: AftercareThreadData


Card = Annotated[
    Union[
        HospitalListCard, HospitalSuggestionsCard, HospitalDetailCard, PriceListCard, SourcesCard,
        TimeSlotsCard, BookingDraftCard, BookingListCard, AftercareThreadCard,
    ],
    Field(discriminator="type"),
]
CARD_ADAPTER: TypeAdapter[Card] = TypeAdapter(Card)


# ------------------------------------------------------------------ API 입출력
class AskRequest(_Model):
    session_id: str | None = None  # 없으면 새 대화
    message: str = Field(min_length=1, max_length=1000)
    # 옛 코드(zh, zh-Hans 등)도 받고 서비스(normalize_language)가 UI_LANGUAGES로 정리한다. 지원하지 않는 값은 거기서 422
    language: str = Field(min_length=2, max_length=10)


class ChatResponse(_Model):
    session_id: str
    text: str
    cards: list[Card]
    ai_generated: bool  # 화면에 "AI 생성" 표시 (인공지능기본법 제31조). 응급 고정 문구는 False
    blocked: bool  # 응급 표현 → 119 안내로 종료
    medical_notice: bool  # "의료 상담이 아닙니다" 고지를 함께 보여줌
