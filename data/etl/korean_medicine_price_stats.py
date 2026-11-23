"""심평원 누리집 비급여 진료비 (대구 전체) → 한방 항목별 가격 범위

nonpay_price_stats.py(내과·안과)와 같은 방법:
- 입력: data/raw/비급여진료/대구_비급여진료비_전체.csv (심평원 누리집 내려받기, 공개기준 2026-08)
- 폐업 판정 기관 제외: data/processed/daegu_hospital_status.csv (verdict == '폐업', 이름+시군구로 맞춤)
- 같은 기관에 같은 항목이 여러 행이면 기관별 최저 금액(최소금액의 최솟값) 1개 → 기관별 값으로 통계

출력
- data/processed/daegu_korean_medicine_price_stats.csv  항목·범위(한의원/한방병원/전체)별 기관 수·최소·최대·평균·중앙값·하위10%·상위10%
- apps/web-platform/src/features/price-info/koreanMedicinePrices.ts  웹 가격 가이드용 (전체 범위의 하위 10% ~ 상위 10%)

웹에는 최소~최대 대신 하위 10%~상위 10%를 보여 줌: 최소가 0원·100원처럼 이벤트·입력 오류로 보이는 값이 섞여 있어서
실행: python -I -X utf8 data/etl/korean_medicine_price_stats.py   (표준 라이브러리만 씀)
"""
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data/raw/비급여진료/대구_비급여진료비_전체.csv'
STATUS = ROOT / 'data/processed/daegu_hospital_status.csv'
OUT = ROOT / 'data/processed/daegu_korean_medicine_price_stats.csv'
TS = ROOT / 'apps/web-platform/src/features/price-info/koreanMedicinePrices.ts'

BASE_MONTH = '202608'
SOURCE = '심평원 누리집 비급여 진료비 정보 (대구 전체 내려받기)'

# (웹 이름, 단위, 조건) — 대분류 '한방' 행 중에서 고름. 웹 이름은 procedures.ts의 ko와 같아야 함
ITEMS = [
    ('단순추나', '1회', lambda r: r['소분류'] == '추나요법' and r['상세분류'] == '단순추나'),
    ('복잡추나', '1회', lambda r: r['소분류'] == '추나요법' and r['상세분류'] == '복잡추나'),
    ('특수추나', '1회 (탈구 · 내장기·두개천골)', lambda r: r['소분류'] == '추나요법' and r['상세분류'].startswith('특수')),
    ('약침술', '1회 (경혈)', lambda r: r['소분류'] == '약침술'),
    ('경근간섭저주파요법', '1회', lambda r: r['소분류'] == '한방물리요법' and r['상세분류'] == '경근간섭저주파요법'),
    ('경피전기자극요법', '1회', lambda r: r['소분류'] == '한방물리요법' and r['상세분류'] == '경피전기자극요법'),
    ('경피온열검사', '1회 (전신)', lambda r: r['소분류'] == '경피온열검사' and r['상세분류'] == '전신'),
    ('사상체질검사', '1회 (QSCC II 설문 · 상담 포함/미포함)', lambda r: r['소분류'] == '사상체질검사'),
    ('한방 향기요법', '1회', lambda r: r['소분류'] == '한방 향기요법'),
]
SCOPES = [('한의원', {'한의원'}), ('한방병원', {'한방병원'}), ('전체', None)]


def key(name, sggu):
    return re.sub(r'\s', '', name) + '|' + sggu


def pct(vals, q):
    # 최근접 순위 백분위 (값이 실제 기관 금액 중 하나가 되게)
    s = sorted(vals)
    i = max(0, min(len(s) - 1, round(q * (len(s) - 1))))
    return s[i]


def main():
    closed = set()
    with STATUS.open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['verdict'] == '폐업':
                closed.add(key(r['yadmNm'], r['sgguCdNm']))
    with SRC.open(encoding='utf-8-sig') as f:
        rows = [r for r in csv.DictReader(f) if r['대분류'] == '한방' and key(r['의료기관명'], r['시군구']) not in closed]

    out, web = [], {}
    for name, unit, cond in ITEMS:
        per = defaultdict(lambda: {'v': None, 'size': ''})
        for r in rows:
            if not cond(r):
                continue
            try:
                v = float(r['최소금액'])
            except ValueError:
                continue
            p = per[r['요양기관ID']]
            p['v'] = v if p['v'] is None else min(p['v'], v)
            p['size'] = r['의료기관규모']
        for scope, sizes in SCOPES:
            vals = [p['v'] for p in per.values() if sizes is None or p['size'] in sizes]
            row = {'진료과': '한방', '항목': name, '단위': unit, '범위': scope, '기관수': len(vals)}
            if vals:
                row.update({'최소': int(min(vals)), '최대': int(max(vals)), '평균': int(round(statistics.mean(vals))),
                            '중앙값': int(round(statistics.median(vals))), '하위10%': int(pct(vals, 0.1)), '상위10%': int(pct(vals, 0.9))})
            row.update({'공개기준년월': BASE_MONTH, '출처': SOURCE})
            out.append(row)
            if scope == '전체' and vals:
                web[name] = (int(pct(vals, 0.1)), int(pct(vals, 0.9)), len(vals))

    cols = ['진료과', '항목', '단위', '범위', '기관수', '최소', '최대', '평균', '중앙값', '하위10%', '상위10%', '공개기준년월', '출처']
    with OUT.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    lines = [
        '// 자동 생성: data/etl/korean_medicine_price_stats.py → data/processed/daegu_korean_medicine_price_stats.csv',
        f'// {SOURCE}, 공개기준 {BASE_MONTH[:4]}-{BASE_MONTH[4:]} · 대구 한의원·한방병원 기관별 최저 금액의 하위 10% ~ 상위 10%',
        '// 내국인 기준 공개 금액 → 외국인 실제 진료비와 다를 수 있음 (가격 가이드 공통 고지)',
        f"export const KMED_PRICE_DATE = '{BASE_MONTH[:4]}-{BASE_MONTH[4:]}';",
        'export const KMED_PRICES: Record<string, { min: number; max: number; clinics: number }> = {',
    ]
    for name, (lo, hi, n) in web.items():
        lines.append(f"  '{name}': {{ min: {lo}, max: {hi}, clinics: {n} }},")
    lines.append('};')
    TS.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f'폐업 제외 {len(closed)}곳 기준 · 한방 행 {len(rows)}개')
    for name, (lo, hi, n) in web.items():
        print(f'  {name}: {lo:,}~{hi:,}원 ({n}곳)')


if __name__ == '__main__':
    main()
