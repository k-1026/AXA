"""대구 피부과 홈페이지 가격 수집본 → 표준 시술(단위 고정)별 최소·최대·평균·중앙값

입력
- data/raw/비급여진료/대구_피부과_홈페이지_정가.xlsx  (팀원 수집, 2026-11-03, 301곳 중 가격 있는 88곳 4,785행)
  - '가격 상세' 시트: 병원명, 항목(홈페이지 표기), 정가, 할인가, 가격 유형, 부터(~) 표기, 구분, 출처 URL
- data/interim/영업정보/daegu_hospitals.csv, data/processed/daegu_hospital_status.csv → 전화번호로 심평원 기관과 매칭해 영업 여부 확인

출력
- data/processed/daegu_derm_homepage_price_stats.csv     표준 시술별 기관 수·최소·최대·평균·중앙값
- data/interim/비급여진료/derm_homepage_price_matched.csv  기관별로 어떤 원문 항목이 어떤 표준 시술로 잡혔는지 (검수용)

규칙
- 이벤트가(정가 미표시)는 쓰지 않음, 정가 칸만 사용 (compliance: 이벤트 할인가 노출 X)
- 이름에 체험·한정·이벤트·첫방문·1+1·패키지·N회(2회 이상)·'+' 조합·'中 선택'·바디가 있으면 제외
- '~부터' 가격 제외 (시작가는 최소·평균을 낮춤)
- 표준 시술마다 단위를 고정 (예: 울쎄라 100샷). 단위가 이름에 없으면 제외
- 같은 기관에 같은 표준 시술이 여러 행이면 기관별 최저 1개 → 기관별 값으로 통계 (심평원 통계와 같은 방식)
- 기관 5곳 미만은 `usable=N` (화면·필터에 쓰지 않음, backend-plan price_stats 규칙)
실행: py data/etl/derm_homepage_price_stats.py
"""
import re
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data/raw/비급여진료/대구_피부과_홈페이지_정가.xlsx'
HIRA = ROOT / 'data/interim/영업정보/daegu_hospitals.csv'
STATUS = ROOT / 'data/processed/daegu_hospital_status.csv'
OUT = ROOT / 'data/processed/daegu_derm_homepage_price_stats.csv'
MATCHED = ROOT / 'data/interim/비급여진료/derm_homepage_price_matched.csv'

LIST_PRICE_TYPES = {'비급여 고지가', '할인 전 정가', '할인 전 정가(추정)', '정가', '표시가(할인 표시 없음)'}
EXCLUDE = re.compile(r'체험|한정|이벤트|EVENT|event|첫방문|재방문|\[\d+월\]|특가|1\+1|할인|무한|혜택|패키지|선물'
                     r'|바디|힙|\+|中|선택|[2-9]\s*회|1\d\s*회|더해')
MIN_N = 5

# (표준 시술, 단위, 포함 정규식, 제외 정규식)
ITEMS = [
    ('턱 보톡스 (국산)', '1회 (양쪽)', r'(?:사각턱|턱)\s*보톡스|턱\s*톡스', r'수입|독일|미국|제오민|제품별|침샘|이중턱|턱라인|턱끝|자갈턱|이마'),
    ('스킨보톡스 얼굴전체 (국산)', '1회', r'스킨\s*보톡스', r'수입|제품별|턱라인|목|이마'),
    ('필러 (국산, 일반 부위)', '1cc', r'국산.*필러.*1\s*cc|필러.*국산.*1\s*cc', r'코|귀|어깨|쇄골|턱끝|주름|입술|이마|애교|요정|V라인'),
    ('울쎄라', '100샷', r'울쎄라.*\b100\s*(?:샷|s)\b', r''),
    ('울쎄라', '300샷', r'울쎄라.*\b300\s*(?:샷|s)\b', r''),
    ('슈링크', '300샷', r'슈링크.*\b300\s*샷', r''),
    ('써마지 FLX', '300샷', r'써마지.*\b300\s*샷', r''),
    ('리쥬란 힐러', '2cc 1회', r'리쥬란\s*힐러.*2\s*cc', r'HB|아이'),
    ('아쿠아필 (얼굴)', '1회', r'아쿠아필', r'코&볼|등|/|:|,(?!\s*얼굴)'),
    ('겨드랑이 레이저 제모', '1회', r'겨드랑이.*제모|제모.*겨드랑이', r'인중|/'),
    ('피코토닝', '1회', r'피코\s*토닝.*1\s*회', r''),
]
NOT_COMPUTED = '인모드·온다·쥬베룩·실리프팅·일반 레이저 제모(부위 다양): 이름에 단위가 거의 없어 같은 시술로 묶을 수 없음'


def digits(s):
    return re.sub(r'\D', '', str(s or ''))


def load():
    wb = openpyxl.load_workbook(SRC, data_only=True)
    cols = ['순번', '병원명', '항목', '정가', '할인가', '가격유형', '부터', '구분', '출처URL']
    d = pd.DataFrame(wb['가격 상세'].iter_rows(min_row=2, values_only=True), columns=cols)
    h = pd.DataFrame(wb['대구 피부과'].iter_rows(min_row=2, max_col=10, values_only=True),
                     columns=['순번', '병원명', '카테고리', '주소', '전화번호', '홈페이지', '블로그', '인스타그램', '기타', '네이버'])
    return d, h


def hira_status(h):
    """전화번호로 심평원 기관 매칭 → 영업 판정 (지역번호 포함 숫자 일치)"""
    hosp = pd.read_csv(HIRA, encoding='utf-8-sig', dtype=str)
    st = pd.read_csv(STATUS, encoding='utf-8-sig', dtype=str)[['ykiho', 'verdict']]
    hosp['tel'] = hosp['telno'].map(digits)
    hosp = hosp.merge(st, on='ykiho', how='left')
    tel = hosp.drop_duplicates('tel').set_index('tel')
    h = h.copy()
    h['tel'] = h['전화번호'].map(digits)
    h['hira_name'] = h['tel'].map(tel['yadmNm'])
    h['verdict'] = h['tel'].map(tel['verdict'])
    return h[['병원명', 'tel', 'hira_name', 'verdict']]


def match(d):
    d = d[d['정가'].notna() & d['가격유형'].isin(LIST_PRICE_TYPES) & d['부터'].isna() & (d['구분'] == '시술')].copy()
    d['항목'] = d['항목'].astype(str)
    d = d[~d['항목'].str.contains(EXCLUDE)]
    rows = []
    for item, unit, inc, exc in ITEMS:
        m = d[d['항목'].str.contains(inc, regex=True)]
        if exc:
            m = m[~m['항목'].str.contains(exc, regex=True)]
        for _, r in m.iterrows():
            rows.append(dict(표준시술=item, 단위=unit, 병원명=r['병원명'], 원문항목=r['항목'],
                             정가=int(r['정가']), 가격유형=r['가격유형'], 출처URL=r['출처URL']))
    return pd.DataFrame(rows)


def stats(m):
    out = []
    for (item, unit), g in m.groupby(['표준시술', '단위'], sort=False):
        per = g.sort_values('정가').groupby('병원명').first()
        v = per['정가']
        out.append(dict(
            표준시술=item, 단위=unit, 기관수=len(per), 최소=int(v.min()), 최대=int(v.max()),
            평균=int(round(v.mean())), 중앙값=int(round(v.median())),
            비급여고지가_기관수=int((per['가격유형'] == '비급여 고지가').sum()),
            usable='Y' if len(per) >= MIN_N else 'N',
        ))
    for item, unit, *_ in ITEMS:
        if not any(o['표준시술'] == item and o['단위'] == unit for o in out):
            out.append(dict(표준시술=item, 단위=unit, 기관수=0, usable='N'))
    s = pd.DataFrame(out)
    s['수집일'] = '2026-11-03'
    s['출처'] = '대구 피부과 병원 홈페이지 가격표 (팀원 수집)'
    return s


def main():
    d, h = load()
    st = hira_status(h)
    priced = st[st['병원명'].isin(d['병원명'].unique())]
    m = match(d)
    s = stats(m)
    MATCHED.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(MATCHED, index=False, encoding='utf-8-sig')
    s.to_csv(OUT, index=False, encoding='utf-8-sig')
    print(f'가격 있는 기관 {len(priced)}곳: 심평원 전화번호 매칭 {priced["hira_name"].notna().sum()}곳, '
          f'판정 {priced["verdict"].value_counts(dropna=False).to_dict()}')
    used = st[st['병원명'].isin(m['병원명'])]
    print(f'통계에 쓰인 기관 {len(used)}곳: 판정 {used["verdict"].value_counts(dropna=False).to_dict()}')
    print('산출 안 함:', NOT_COMPUTED)
    print(s.to_string())


if __name__ == '__main__':
    main()
