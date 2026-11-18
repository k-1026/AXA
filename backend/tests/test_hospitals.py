"""병원 정보: 모든 병원을 보여 주되, 상담·예약 요청은 등록 유치의료기관만 (compliance 2-1, 해외진출법 제24조①3).

적재(`load_hospitals`)는 공공데이터 CSV 경로를 받아 DB에 넣고, 결과는 API로만 확인한다.
"""

import csv

import pytest
from sqlalchemy.orm import Session

from modules.hospital.loader import load_hospitals

HOSP_COLS = ["ykiho", "yadmNm", "clCd", "clCdNm", "sgguCdNm", "addr", "telno", "XPos", "YPos", "hospUrl"]


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return path


def hosp(ykiho, name, **kw):
    row = {
        "ykiho": ykiho,
        "yadmNm": name,
        "clCd": "31",
        "clCdNm": "의원",
        "sgguCdNm": "대구중구",
        "addr": "대구광역시 중구 어딘가 1",
        "telno": "053-000-0000",
        "XPos": "128.60",
        "YPos": "35.87",
        "hospUrl": "",
    }
    row.update(kw)
    return row


@pytest.fixture
def files(tmp_path):
    """테스트마다 필요한 CSV만 만들어 경로를 돌려준다."""

    def make(hospitals, registered=None, status=None, hours=None):
        out = {"hospitals_csv": write_csv(tmp_path / "h.csv", HOSP_COLS, hospitals)}
        if registered is not None:
            out["registered_csv"] = write_csv(
                tmp_path / "r.csv", ["registration_no", "name_en", "address_en", "ykiho"], registered
            )
        if status is not None:
            out["status_csv"] = write_csv(tmp_path / "s.csv", ["ykiho", "verdict"], status)
        if hours is not None:
            cols = sorted({k for r in hours for k in r})
            out["hours_csv"] = write_csv(tmp_path / "t.csv", cols, hours)
        return out

    return make


def load(db_engine, **paths):
    with Session(db_engine) as db:
        result = load_hospitals(db, **paths)
        db.commit()
    return result


def list_hospitals(client, **params):
    r = client.get("/api/v1/hospitals", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_목록은_모든_병원을_보여주고_요청은_등록_병원만(client, db_engine, files):
    load(
        db_engine,
        **files(
            [hosp("Y1", "등록의원"), hosp("Y2", "미등록의원")],
            registered=[{"registration_no": "M-1", "name_en": "Registered Clinic", "ykiho": "Y1"}],
        ),
    )

    items = {h["ykiho"]: h for h in list_hospitals(client)}

    assert set(items) == {"Y1", "Y2"}
    assert items["Y1"]["is_registered_facility"] is True
    assert items["Y1"]["can_request"] is True
    assert items["Y1"]["name_en"] == "Registered Clinic"
    assert items["Y2"]["is_registered_facility"] is False
    assert items["Y2"]["can_request"] is False


def test_폐업_병원은_목록에서_빠지고_재적재로_사라진_병원은_폐업_처리(client, db_engine, files):
    load(
        db_engine,
        **files(
            [hosp("Y1", "가"), hosp("Y2", "나"), hosp("Y3", "다")],
            status=[{"ykiho": "Y1", "verdict": "정상"}, {"ykiho": "Y2", "verdict": "폐업"},
                    {"ykiho": "Y3", "verdict": "정상"}],
        ),
    )
    first = {h["ykiho"]: h["id"] for h in list_hospitals(client)}
    assert set(first) == {"Y1", "Y3"}

    # 다시 적재: Y3이 새 파일에 없음 → 목록에서 빠지고, Y1의 id는 그대로
    load(db_engine, **files([hosp("Y1", "가")], status=[{"ykiho": "Y1", "verdict": "정상"}]))
    again = {h["ykiho"]: h["id"] for h in list_hospitals(client)}
    assert again == {"Y1": first["Y1"]}


def test_필터_지역_진료과_등록여부(client, db_engine, files):
    load(
        db_engine,
        **files(
            [hosp("Y1", "중구피부과", sgguCdNm="대구중구"), hosp("Y2", "수성피부과", sgguCdNm="대구수성구"),
             hosp("Y3", "수성성형외과", sgguCdNm="대구수성구")],
            registered=[{"registration_no": "M-2", "ykiho": "Y2"}],
            hours=[{"ykiho": "Y1", "has_dermatology": "Y"}, {"ykiho": "Y2", "has_dermatology": "Y"},
                   {"ykiho": "Y3", "has_plastic_surgery": "Y"}],
        ),
    )

    def ykihos(**p):
        return [h["ykiho"] for h in list_hospitals(client, **p)]

    assert ykihos(sggu="대구수성구") == ["Y3", "Y2"]  # 이름순
    assert ykihos(dept="dermatology") == ["Y2", "Y1"]
    assert ykihos(registered="true") == ["Y2"]
    assert ykihos(sggu="대구수성구", dept="dermatology") == ["Y2"]


def test_정렬은_이름_거리만_그_밖은_422(client, db_engine, files):
    load(
        db_engine,
        **files([hosp("NEAR", "하늘의원", XPos="128.600", YPos="35.870"),
                 hosp("FAR", "가나의원", XPos="128.700", YPos="35.900")]),
    )

    assert [h["ykiho"] for h in list_hospitals(client, sort="name")] == ["FAR", "NEAR"]
    near_first = list_hospitals(client, sort="distance", lat=35.870, lng=128.600)
    assert [h["ykiho"] for h in near_first] == ["NEAR", "FAR"]
    assert near_first[0]["distance_km"] == 0.0
    assert 9 < near_first[1]["distance_km"] < 10  # 직선거리 약 9.6km

    for bad in ({"sort": "registered"}, {"sort": "popular"}, {"sort": "distance"}):
        r = client.get("/api/v1/hospitals", params=bad)
        assert r.status_code == 422
        assert r.json()["code"] == "validation"


def test_ids로_여러_병원_기본정보(client, db_engine, files):
    load(db_engine, **files([hosp("Y1", "가"), hosp("Y2", "나"), hosp("Y3", "다")]))
    ids = {h["ykiho"]: h["id"] for h in list_hospitals(client)}

    got = list_hospitals(client, ids=f"{ids['Y3']},{ids['Y1']}")
    assert sorted(h["ykiho"] for h in got) == ["Y1", "Y3"]


def test_상세는_진료시간_출처_포함_미등록도_정보는_준다(client, db_engine, files):
    load(
        db_engine,
        **files(
            [hosp("Y1", "미등록의원", hospUrl="http://example.test")],
            hours=[{"ykiho": "Y1", "trmtMonStart": "0900", "trmtMonEnd": "1800",
                    "trmtWedStart": "0000", "trmtWedEnd": "0000",
                    "lunchWeek": "12시30분~13시30분", "noTrmtSun": "전부 휴무"}],
        ),
    )
    hid = list_hospitals(client)[0]["id"]

    r = client.get(f"/api/v1/hospitals/{hid}")
    assert r.status_code == 200
    d = r.json()
    assert d["can_request"] is False
    assert d["homepage"] == "http://example.test"
    assert d["source"] and d["fetched_at"]
    days = {h["day"]: h for h in d["hours"]}
    assert [h["day"] for h in d["hours"]] == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    assert (days["mon"]["state"], days["mon"]["open_time"], days["mon"]["close_time"]) == ("open", "09:00:00", "18:00:00")
    assert (days["mon"]["lunch_start"], days["mon"]["lunch_end"]) == ("12:30:00", "13:30:00")
    assert days["tue"]["state"] == "unknown"  # 값이 없으면 휴진으로 단정하지 않음
    assert days["wed"]["state"] == "unknown"  # 원본 "0000~0000"은 진료로 보지 않음
    assert days["sun"]["state"] == "closed"


def test_폐업한_등록_병원은_상세는_보이지만_요청은_불가(client, db_engine, files):
    load(
        db_engine,
        **files([hosp("Y1", "폐업등록의원")], registered=[{"registration_no": "M-3", "ykiho": "Y1"}],
                status=[{"ykiho": "Y1", "verdict": "폐업"}]),
    )
    hid = list_hospitals(client, ids="1")[0]["id"]

    d = client.get(f"/api/v1/hospitals/{hid}").json()
    assert (d["is_registered_facility"], d["status_verdict"], d["can_request"]) == (True, "closed", False)


def test_없는_병원은_404(client, db_engine):
    r = client.get("/api/v1/hospitals/999")
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


def test_get_basic_다른_모듈용_기본정보(db_engine, files):
    from modules.hospital import service

    load(db_engine, **files([hosp("Y1", "등록의원"), hosp("Y2", "미등록의원")],
                            registered=[{"registration_no": "M-1", "ykiho": "Y1"}]))
    with Session(db_engine) as db:
        by_ykiho = {b.ykiho: b for b in (service.get_basic(db, i) for i in (1, 2))}
        assert by_ykiho["Y1"].name_ko == "등록의원" and by_ykiho["Y1"].can_request is True
        assert by_ykiho["Y2"].can_request is False
        with pytest.raises(Exception) as e:
            service.get_basic(db, 999)
        assert getattr(e.value, "code", None) == "not_found"


def test_require_requestable_등록_안됐거나_영업중_아니면_403(db_engine, files):
    from core.errors import AppError
    from modules.hospital import service

    load(db_engine, **files(
        [hosp("Y1", "등록의원"), hosp("Y2", "미등록의원"), hosp("Y3", "폐업등록의원")],
        registered=[{"registration_no": "M-1", "ykiho": "Y1"}, {"registration_no": "M-3", "ykiho": "Y3"}],
        status=[{"ykiho": "Y1", "verdict": "정상"}, {"ykiho": "Y2", "verdict": "정상"}, {"ykiho": "Y3", "verdict": "폐업"}],
    ))
    with Session(db_engine) as db:
        assert service.require_requestable(db, 1).ykiho == "Y1"
        for hid, reason in ((2, "unregistered"), (3, "not_operating")):
            with pytest.raises(AppError) as e:
                service.require_requestable(db, hid)
            assert (e.value.status_code, e.value.code, e.value.detail) == (403, "hospital.not_requestable", {"reason": reason})
        with pytest.raises(AppError) as e:
            service.require_requestable(db, 999)
        assert e.value.code == "not_found"


def test_요일_필터는_그_요일_진료가_확인된_병원만(client, db_engine, files):
    load(db_engine, **files(
        [hosp("SAT", "토요일진료의원"), hosp("WEEK", "평일의원"), hosp("NOHRS", "시간모름의원")],
        hours=[{"ykiho": "SAT", "trmtMonStart": "0900", "trmtMonEnd": "1800", "trmtSatStart": "0900", "trmtSatEnd": "1300"},
               {"ykiho": "WEEK", "trmtMonStart": "0900", "trmtMonEnd": "1800"}],
    ))
    assert [h["ykiho"] for h in list_hospitals(client, open_on="sat")] == ["SAT"]
    assert sorted(h["ykiho"] for h in list_hospitals(client, open_on="mon")) == ["SAT", "WEEK"]
    assert client.get("/api/v1/hospitals", params={"open_on": "holiday"}).status_code == 422


def test_피부과는_이름에_피부과가_있는_전문_병원만(client, db_engine, files):
    load(db_engine, **files(
        [hosp("D1", "맑은피부과의원"), hosp("D2", "튼튼정형외과의원"), hosp("D3", "대학교병원", clCdNm="상급종합")],
        hours=[{"ykiho": k, "has_dermatology": "Y"} for k in ("D1", "D2", "D3")],
    ))
    assert [h["ykiho"] for h in list_hospitals(client, dept="dermatology")] == ["D1"]


def test_성형외과도_이름에_성형외과가_있는_전문_병원만(client, db_engine, files):
    load(db_engine, **files(
        [hosp("P1", "예쁜성형외과의원"), hosp("P2", "바른피부과의원"), hosp("P3", "대학교병원", clCdNm="상급종합")],
        hours=[{"ykiho": k, "has_plastic_surgery": "Y"} for k in ("P1", "P2", "P3")],
    ))
    assert [h["ykiho"] for h in list_hospitals(client, dept="plastic")] == ["P1"]


def test_진료과목_json에_BOM이_있어도_적재(client, db_engine, files, tmp_path):
    import json

    dg = tmp_path / "dg.json"
    dg.write_text(json.dumps({"items": {"01": [{"ykiho": "I1"}]}}), encoding="utf-8-sig")  # PowerShell 저장 형식
    load(db_engine, **files([hosp("I1", "내과의원")]), dgsbjt_json=dg)
    assert [h["ykiho"] for h in list_hospitals(client, dept="internal")] == ["I1"]


# ── 직접 채운 진료시간 (등록 유치기관 빈칸, docs/진료시간-채움-등록기관-2026-11-18.md) ──

MANUAL_COLS = ["ykiho", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
               "lunch_week", "lunch_sat", "holiday", "source_grade", "source_url", "checked_at", "note"]


def detail_hours(client, hid):
    r = client.get(f"/api/v1/hospitals/{hid}")
    assert r.status_code == 200, r.text
    return {h["day"]: h for h in r.json()["hours"]}


def test_직접_채운_진료시간은_API에_없는_요일만_채운다(client, db_engine, files, tmp_path):
    paths = files(
        [hosp("Y1", "등록의원")],
        registered=[{"registration_no": "M-1", "ykiho": "Y1"}],
        hours=[{"ykiho": "Y1", "trmtMonStart": "0900", "trmtMonEnd": "1800", "noTrmtSun": ""}],
    )
    paths["manual_hours_csv"] = write_csv(tmp_path / "m.csv", MANUAL_COLS, [{
        "ykiho": "Y1", "mon": "10:00-20:00", "tue": "10:00-19:00", "wed": "휴진", "thu": "",
        "sat": "09:30-15:30", "lunch_week": "13:00-14:00", "lunch_sat": "",
        "source_grade": "공식", "source_url": "https://clinic.example.test/hours", "checked_at": "2026-11-18",
    }])
    result = load(db_engine, **paths)
    assert result["manual_hours"] == 1
    days = detail_hours(client, list_hospitals(client)[0]["id"])

    # API 값이 있으면 API 우선
    assert (days["mon"]["open_time"], days["mon"]["close_time"]) == ("09:00:00", "18:00:00")
    assert days["mon"]["source"].startswith("건강보험심사평가원")
    # API 빈칸은 직접 채운 값, 출처·확인일은 그 행 것
    assert (days["tue"]["state"], days["tue"]["open_time"], days["tue"]["close_time"]) == ("open", "10:00:00", "19:00:00")
    assert (days["tue"]["lunch_start"], days["tue"]["lunch_end"]) == ("13:00:00", "14:00:00")
    assert days["tue"]["source"] == "https://clinic.example.test/hours"
    assert days["tue"]["checked_at"].startswith("2026-11-18")
    assert days["sat"]["state"] == "open" and days["sat"]["lunch_start"] is None
    # "휴진" = closed, 빈칸 = unknown (휴진으로 단정 X)
    assert days["wed"]["state"] == "closed" and days["wed"]["open_time"] is None
    assert days["thu"]["state"] == "unknown"


def test_API_진료시간_행이_없어도_직접_채운_값으로_적재(client, db_engine, files, tmp_path):
    paths = files([hosp("Y1", "등록의원")], registered=[{"registration_no": "M-1", "ykiho": "Y1"}])
    paths["manual_hours_csv"] = write_csv(tmp_path / "m.csv", MANUAL_COLS, [{
        "ykiho": "Y1", "mon": "9:00-18:00", "fri": "10:00-24:00", "sun": "휴진",
        "source_url": "https://clinic.example.test", "checked_at": "2026-11-18",
    }])
    load(db_engine, **paths)
    hid = list_hospitals(client)[0]["id"]
    days = detail_hours(client, hid)
    assert [d for d in days] == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    assert days["mon"]["open_time"] == "09:00:00"
    assert days["fri"]["close_time"] == "23:59:00"  # 24:00 → 23:59
    assert days["sun"]["state"] == "closed"
    assert days["tue"]["state"] == "unknown"
    # 요일 필터도 직접 채운 값으로 걸린다
    assert [h["id"] for h in list_hospitals(client, open_on="mon")] == [hid]


def test_형식이_틀린_직접_채운_값은_무시하고_unknown(client, db_engine, files, tmp_path):
    paths = files([hosp("Y1", "등록의원")], registered=[{"registration_no": "M-1", "ykiho": "Y1"}])
    paths["manual_hours_csv"] = write_csv(tmp_path / "m.csv", MANUAL_COLS, [{
        "ykiho": "Y1", "mon": "오전 10시~", "tue": "19:00-10:00", "wed": "25:00-26:00",
        "source_url": "https://clinic.example.test", "checked_at": "2026-11-18",
    }])
    load(db_engine, **paths)
    days = detail_hours(client, list_hospitals(client)[0]["id"])
    assert {days[d]["state"] for d in ("mon", "tue", "wed")} == {"unknown"}
    assert days["mon"]["source"].startswith("건강보험심사평가원")


def test_출처_없는_직접_채운_행은_적재하지_않는다(client, db_engine, files, tmp_path):
    paths = files([hosp("Y1", "등록의원")], registered=[{"registration_no": "M-1", "ykiho": "Y1"}])
    paths["manual_hours_csv"] = write_csv(tmp_path / "m.csv", MANUAL_COLS, [{"ykiho": "Y1", "mon": "10:00-19:00"}])
    result = load(db_engine, **paths)
    assert result["manual_hours"] == 0
    assert detail_hours(client, list_hospitals(client)[0]["id"])["mon"]["state"] == "unknown"


def test_override_Y면_API_값도_검증한_값으로_바꾼다(client, db_engine, files, tmp_path):
    # 2026-11-18 카카오맵 영업정보 검증: 심평원 API 값이 실제와 다른 곳은 override=Y로 덮어씀
    paths = files(
        [hosp("Y1", "등록의원")],
        registered=[{"registration_no": "M-1", "ykiho": "Y1"}],
        hours=[{"ykiho": "Y1", "trmtMonStart": "0900", "trmtMonEnd": "1800",
                "trmtTueStart": "0900", "trmtTueEnd": "1800", "noTrmtSun": ""}],
    )
    paths["manual_hours_csv"] = write_csv(tmp_path / "m.csv", MANUAL_COLS + ["override"], [{
        "ykiho": "Y1", "mon": "10:00-20:00", "tue": "", "sat": "휴진", "lunch_week": "13:00-14:00",
        "source_url": "https://place.example.test/1", "checked_at": "2026-11-18", "override": "Y",
    }])
    load(db_engine, **paths)
    days = detail_hours(client, list_hospitals(client)[0]["id"])
    assert (days["mon"]["open_time"], days["mon"]["close_time"]) == ("10:00:00", "20:00:00")
    assert days["mon"]["source"] == "https://place.example.test/1"
    assert days["tue"]["open_time"] == "09:00:00"  # 검증 값이 빈 요일은 API 그대로
    assert days["tue"]["source"].startswith("건강보험심사평가원")
    assert days["sat"]["state"] == "closed"
