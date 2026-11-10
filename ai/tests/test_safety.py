"""ai/llm/safety.py 테스트 — 응급 차단, 개인정보 마스킹, 의료 판단·병원 평가 분류."""

import pytest

from ai.llm.safety import check, mask_pii


@pytest.mark.parametrize("text,lang", [
    ("I have chest pain and can't breathe", "en"),
    ("가슴이 아파요 숨이 안 쉬어져요", "ko"),
    ("手术后流血不止", "zh"),
    ("Tôi bị khó thở sau phẫu thuật", "vi"),
    ("胸が痛いです", "ja"),
])
def test_emergency_is_blocked_with_119(text, lang):
    r = check(text, lang)
    assert r.action == "block" and r.categories == ["emergency"] and "119" in r.reply


def test_emergency_reply_adds_english_for_other_languages():
    assert "Call 119" in check("khó thở", "vi").reply
    assert "Call 119" in check("chest pain", "xx").reply  # 모르는 언어 코드 → 영어


@pytest.mark.parametrize("text,cat", [
    ("이거 무슨 병인가요?", "diagnosis"),
    ("Is this cancer?", "diagnosis"),
    ("레이저 부작용 있나요?", "treatment_judgment"),
    ("Is fractional laser safe? does it work?", "treatment_judgment"),
    ("Should I get botox or filler?", "treatment_judgment"),
    ("激光治疗痘疤效果好吗？", "treatment_judgment"),
    ("Can I take ibuprofen after the procedure?", "medication"),
    ("대구에서 제일 잘하는 피부과 추천해 주세요", "hospital_ranking"),
    ("Which clinic is the best?", "hospital_ranking"),
    ("给我推荐一家最好的皮肤科", "hospital_ranking"),
    ("Bệnh viện nào tốt nhất?", "hospital_ranking"),
    ("おすすめの皮膚科は？", "hospital_ranking"),
    ("Do I have skin cancer?", "diagnosis"),
    ("이 약 먹어도 되나요?", "medication"),
    ("여기 병원 어때요?", "hospital_ranking"),
    ("Is Demo Clinic A any good?", "hospital_ranking"),
    ("쌍꺼풀 수술 받아도 될까요?", "treatment_judgment"),
])
def test_guard_categories(text, cat):
    r = check(text)
    assert r.action == "guard" and cat in r.categories and r.note and r.reply is None


@pytest.mark.parametrize("text", [
    "I have acne scars and want treatment in Suseong-gu. I only speak English.",
    "수성구에 영어 되는 피부과 찾아줘",
    "Can I go on December 1st at 10:00?",
    "How much is scar laser treatment?",
    "C-3-3 비자는 어떻게 받나요?",
    "我的预约状态怎么样了？",
    "I need a receipt document from the hospital",
    "I am just visiting Korea for two weeks.",
    "Tôi muốn đặt lịch tư vấn ở bệnh viện 9001 ngày 2026-12-01 10:00",
    # 일상 문장이 잘못 걸리지 않는지 (2026-11-10 점검에서 걸렸던 문장들)
    "Do I have to bring my passport?",
    "Do I have a booking on Dec 1?",
    "What documents should I get before the visit?",
    "Should I have an interpreter?",
    "예약 추천 시간대가 있나요?",
    "용량 큰 파일도 보낼 수 있나요?",
    "Can I take a taxi from the airport?",
    "top floor parking available?",
    "Is clinic A good at English?",
    "Show me the review of my booking draft",
    # 병명만 말한 병원 찾기는 응급이 아님
    "stroke rehabilitation hospitals in Daegu",
    "마비 재활 병원 찾아줘",
])
def test_normal_requests_pass(text):
    r = check(text)
    assert r.action == "pass" and r.categories == [] and r.text == text


def test_mixed_request_is_guarded_not_blocked():
    r = check("I have acne scars. Which clinic in Suseong-gu is best, and can I book for Dec 1?")
    assert r.action == "guard" and "Then help with whatever else" in r.note


def test_mask_pii():
    text, found = mask_pii(
        "mail a.b+c@test.co.kr, tel +82 10-1234-5678 or 053-123-4567, passport M12345678, ARC 900101-5123456"
    )
    assert found == ["email", "arc", "passport", "phone"]
    for secret in ("test.co.kr", "1234-5678", "123-4567", "M12345678", "5123456"):
        assert secret not in text


def test_mask_keeps_dates_times_ids():
    for text in ["2026-12-01 10:00", "hospital 9001 on 2026-12-01", "booking demo-bk-002", "150000 KRW", "Dec 1-3, 2026"]:
        assert mask_pii(text) == (text, [])
