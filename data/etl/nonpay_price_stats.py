"""심평원 누리집 비급여 진료비 (대구 전체) → 내과·안과 항목별 최소·최대·평균

입력
- data/raw/비급여진료/대구_비급여진료비_전체.csv  (심평원 누리집 내려받기, 공개기준 2026-08, 의원급 포함)
- data/interim/영업정보/daegu_nonpay_prices.csv     (공공데이터포털 API 병원급 수집본, 2026-10-28) → 같은 값인지 대조
- data/processed/daegu_hospital_status.csv           (폐업 교차검증) → 폐업 판정 기관 제외

출력
- data/processed/daegu_nonpay_price_stats.csv   항목·범위(의원/병원급/전체)별 기관 수·최소·최대·평균·중앙값
- data/interim/비급여진료/nonpay_api_crosscheck.csv  누리집 vs API 같은 기관·같은 코드 금액 대조

산출: 같은 기관에 같은 항목이 여러 행이면 기관별 최저 금액(최소금액의 최솟값) 1개 → 기관별 값으로 통계
실행: py data/etl/nonpay_price_stats.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data/raw/비급여진료/대구_비급여진료비_전체.csv'
API = ROOT / 'data/interim/영업정보/daegu_nonpay_prices.csv'
STATUS = ROOT / 'data/processed/daegu_hospital_status.csv'
OUT = ROOT / 'data/processed/daegu_nonpay_price_stats.csv'
XCHK = ROOT / 'data/interim/비급여진료/nonpay_api_crosscheck.csv'

CLINIC = {'의원'}
HOSPITAL = {'병원', '종합병원', '상급종합'}

# (진료과, 항목, 단위, docx 값, 조건 함수)
ITEMS = [
    ('내과', '진정내시경 관리료 Ⅱ', '1회', '50,000 (D 수면비)',
     lambda d: d['소분류'].str.strip().eq('진정내시경환자관리료') & d['항목명(전체)'].str.rstrip().str.endswith('Ⅱ')),
    ('내과', '진정내시경 관리료 Ⅲ', '1회', '',
     lambda d: d['소분류'].str.strip().eq('진정내시경환자관리료') & d['항목명(전체)'].str.rstrip().str.endswith('Ⅲ')),
    ('내과', '상복부초음파 (간·담낭·담도·비장·췌장-일반)', '1회', '67,420 (D)',
     lambda d: d['상세분류'].eq('간·담낭·담도·비장·췌장-일반')),
    ('내과', '갑상선초음파 (갑상선·부갑상선)', '1회', '60,000 (F)',
     lambda d: d['상세분류'].eq('갑상선·부갑상선')),
    ('내과', '비뇨기계초음파 (신장·부신)', '1회', '44,940 (D)',
     lambda d: d['소분류'].eq('복부-비뇨기계 초음파') & d['상세분류'].eq('신장·부신')),
    ('내과', 'A형간염 하브릭스 1.0ml', '1회 접종', '80,000 (F)',
     lambda d: d['상세분류'].eq('하브릭스주 1.0ml')),
    ('내과', 'B형간염 유박스비 1.0mL', '1회 접종', '27,000 (F)',
     lambda d: d['소분류'].eq('B형간염') & d['상세분류'].str.startswith('유박스비', na=False) & d['상세분류'].str.contains('1.0', regex=False, na=False)),
    ('내과', 'HPV 가다실9', '1회 접종', '견적 필요',
     lambda d: d['상세분류'].str.startswith('가다실9', na=False)),
    ('안과', '안구광학단층촬영 (OCT)', '항목에 편측·양안 미표기', '50,000/양안 (E)',
     lambda d: d['소분류'].eq('안구광학단층촬영')),
    ('안과', '라식', '양안 추정 (미표기)', '150만/양안 (E, 라식·라섹)',
     lambda d: d['소분류'].eq('레이저각막절삭성형술(라식)')),
    ('안과', '라섹', '양안 추정 (미표기)', '150만/양안 (E, 라식·라섹)',
     lambda d: d['소분류'].eq('레이저각막상피절삭성형술(라섹)')),
    ('안과', '조절성(다초점 등) 인공수정체 — 기관별 최저 제품', '단안, 재료비', '380만~430만/단안 (E)',
     lambda d: d['소분류'].eq('조절성 인공수정체')),
]


def load():
    d = pd.read_csv(SRC, encoding='utf-8-sig', dtype=str)
    for c in ['최소금액', '최대금액']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    return d


def key(name, sggu):
    return re.sub(r'\s', '', str(name)) + '|' + str(sggu)


def drop_closed(d):
    st = pd.read_csv(STATUS, encoding='utf-8-sig', dtype=str)
    closed = {key(n, g) for n, g in st.loc[st['verdict'] == '폐업', ['yadmNm', 'sgguCdNm']].values}
    k = [key(n, g) for n, g in d[['의료기관명', '시군구']].values]
    mask = pd.Series(k, index=d.index).isin(closed)
    return d[~mask], d.loc[mask, '의료기관명'].unique().tolist()


def stats(d):
    rows = []
    for dept, item, unit, docx, cond in ITEMS:
        s = d[cond(d)]
        per = s.groupby('요양기관ID').agg(v=('최소금액', 'min'), vmax=('최대금액', 'max'), 규모=('의료기관규모', 'first'))
        for scope, sizes in [('의원', CLINIC), ('병원급', HOSPITAL), ('전체', None)]:
            p = per if sizes is None else per[per['규모'].isin(sizes)]
            if p.empty:
                rows.append(dict(진료과=dept, 항목=item, 단위=unit, 범위=scope, 기관수=0, docx값=docx))
                continue
            rows.append(dict(
                진료과=dept, 항목=item, 단위=unit, 범위=scope, 기관수=len(p),
                최소=int(p['v'].min()), 최대=int(p['v'].max()),
                평균=int(round(p['v'].mean())), 중앙값=int(round(p['v'].median())),
                최고가_최대금액=int(p['vmax'].max()), docx값=docx,
            ))
    out = pd.DataFrame(rows)
    out['공개기준년월'] = '202608'
    out['출처'] = '심평원 누리집 비급여 진료비 정보 (대구 전체 내려받기)'
    return out


def crosscheck(d):
    api = pd.read_csv(API, encoding='utf-8-sig', dtype=str)
    api['curAmt'] = pd.to_numeric(api['curAmt'], errors='coerce')
    api['k'] = [key(n, g) + '|' + c for n, g, c in api[['yadmNm', 'sgguCdNm', 'npayCd']].values]
    a = api.groupby('k')['curAmt'].min()
    d = d.copy()
    d['k'] = [key(n, g) + '|' + c for n, g, c in d[['의료기관명', '시군구', '비급여코드']].values]
    w = d.groupby('k').agg(name=('의료기관명', 'first'), 규모=('의료기관규모', 'first'),
                           item=('항목명(전체)', 'first'), web=('최소금액', 'min'))
    m = w.join(a.rename('api'), how='inner')
    m['일치'] = (m['web'] == m['api']).map({True: 'Y', False: 'N'})
    return m.reset_index(drop=True)


def main():
    d = load()
    d, closed = drop_closed(d)
    out = stats(d)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, encoding='utf-8-sig')
    m = crosscheck(d)
    XCHK.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(XCHK, index=False, encoding='utf-8-sig')
    print('폐업 판정 제외:', closed)
    print(f'API 대조: 같은 기관·코드 {len(m)}건, 일치 {(m["일치"] == "Y").sum()}건')
    print(out.to_string())


if __name__ == '__main__':
    main()
