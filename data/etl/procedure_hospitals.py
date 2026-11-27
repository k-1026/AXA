"""가격 가이드 시술별 "이 시술을 하는 병원" 목록 = 심평원 비급여 공개 자료 + 병원 홈페이지 수집 (2026-11-27)

- 홈페이지: data/etl/crawl_procedure_homepages.py → data/interim/시술/homepage_procedures.csv (시술 키워드가 나온 쪽 URL을 출처로)
- 한 병원이 두 출처에 다 있으면 심평원(가격 공개) 쪽을 표시

- 병원별 시술 목록은 공개 자료가 따로 없어서, 그 시술(또는 그 시술에만 쓰는 항목)의 비급여 가격을 심평원에 공개한 병원을 "하는 병원"으로 본다
- 쌍꺼풀·보톡스 같은 미용 시술은 심평원 공개 항목이 아니라 목록 없음 → 화면에서 "병원 정보 준비 중"
- 입력: data/raw/비급여진료/대구_비급여진료비_전체.csv (공개기준 2026-08) · apps/web-platform/public/data/hospitals.json (웹 병원 목록)
- 맞춤: 기관명(공백 제거) + 구 이름. 폐업 판정 기관 제외 (data/processed/daegu_hospital_status.csv)

출력: apps/web-platform/src/features/price-info/procedureHospitalData.ts (가격 가이드 화면)
      data/processed/procedure_hospitals.json (챗봇 search_hospitals의 procedure 조건, ai/agent/tools/chat_tools.py)
실행: python -I -X utf8 data/etl/procedure_hospitals.py   (표준 라이브러리만 씀)
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data/raw/비급여진료/대구_비급여진료비_전체.csv'
STATUS = ROOT / 'data/processed/daegu_hospital_status.csv'
HOSPITALS = ROOT / 'apps/web-platform/public/data/hospitals.json'
TS = ROOT / 'apps/web-platform/src/features/price-info/procedureHospitalData.ts'
WEB = ROOT / 'data/interim/시술/homepage_procedures.csv'
PROCEDURES = ROOT / 'apps/web-platform/src/features/price-info/procedures.ts'
CHAT_JSON = ROOT / 'data/processed/procedure_hospitals.json'

BASE_MONTH = '2026-08'
VACCINES = {'인플루엔자(독감)', 'A형간염', 'B형간염', '사람유두종바이러스 감염증(HPV 백신)'}

# (웹 이름 = procedures.ts의 ko, 근거 항목, 조건)
ITEMS = [
    ('위·대장내시경', '진정내시경 환자관리료', lambda r: r['소분류'].strip() == '진정내시경환자관리료'),
    ('복부초음파', '상복부 초음파 (간·담낭·담도·비장·췌장)', lambda r: r['상세분류'].startswith('간·담낭·담도·비장·췌장')),
    ('독감·간염·HPV 백신 접종 상담', '독감·A형간염·B형간염·HPV 백신', lambda r: r['대분류'] == '예방접종료' and r['소분류'] in VACCINES),
    ('라식', '레이저각막절삭성형술(라식)', lambda r: r['소분류'] == '레이저각막절삭성형술(라식)'),
    ('라섹', '레이저각막상피절삭성형술(라섹)', lambda r: r['소분류'] == '레이저각막상피절삭성형술(라섹)'),
    ('백내장 수술·인공수정체 상담', '조절성(다초점 등) 인공수정체', lambda r: r['소분류'] == '조절성 인공수정체'),
    ('단순추나', '추나요법 단순추나', lambda r: r['소분류'] == '추나요법' and r['상세분류'] == '단순추나'),
    ('복잡추나', '추나요법 복잡추나', lambda r: r['소분류'] == '추나요법' and r['상세분류'] == '복잡추나'),
    ('특수추나', '추나요법 특수추나', lambda r: r['소분류'] == '추나요법' and r['상세분류'].startswith('특수')),
    ('약침술', '약침술', lambda r: r['소분류'] == '약침술'),
    ('경근간섭저주파요법', '한방물리요법 경근간섭저주파요법', lambda r: r['소분류'] == '한방물리요법' and r['상세분류'] == '경근간섭저주파요법'),
    ('경피전기자극요법', '한방물리요법 경피전기자극요법', lambda r: r['소분류'] == '한방물리요법' and r['상세분류'] == '경피전기자극요법'),
    ('경피온열검사', '경피온열검사', lambda r: r['소분류'] == '경피온열검사'),
    ('사상체질검사', '사상체질검사', lambda r: r['소분류'] == '사상체질검사'),
    ('한방 향기요법', '한방 향기요법', lambda r: r['소분류'] == '한방 향기요법'),
]


def norm(name):
    return re.sub(r'\s', '', name)


def gu(sggu):
    # 심평원 '대구서구' · 웹 '서구'
    return sggu.replace('대구', '', 1) if sggu.startswith('대구') else sggu


def read_procedures():
    """procedures.ts의 시술 [ko, en] 행과 진료과 키 (화면과 같은 이름을 챗봇도 쓰게)"""
    out, dept = [], None
    for line in PROCEDURES.read_text(encoding='utf-8').splitlines():
        if m := re.search(r"dept: '(\w+)'", line):
            dept = m.group(1)
        for m in re.finditer(r"\[(['\"])(.+?)\1,\s*(['\"])(.+?)\3", line):
            out.append({'ko': m.group(2), 'en': m.group(4), 'dept': dept})
    return out


def main():
    closed = set()
    with STATUS.open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['verdict'] == '폐업':
                closed.add((norm(r['yadmNm']), gu(r['sgguCdNm'])))

    hospitals = json.loads(HOSPITALS.read_text(encoding='utf-8'))['items']
    by_key = defaultdict(list)
    for h in hospitals:
        if not h.get('demo'):
            by_key[(norm(h['name']), h['district'])].append(h['id'])

    ids_ok = {h['id'] for h in hospitals if not h.get('demo')}
    found = defaultdict(dict)  # 시술 → {병원 id: 출처}
    with SRC.open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            k = (norm(r['의료기관명']), gu(r['시군구']))
            if k in closed or k not in by_key:
                continue
            for name, _, cond in ITEMS:
                if cond(r):
                    for i in by_key[k]:
                        found[name][i] = {'src': 'hira'}
    web_date = ''
    with WEB.open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['id'] in ids_ok and r['id'] not in found[r['시술']]:
                found[r['시술']][r['id']] = {'src': 'web', 'url': r['출처URL']}
                web_date = max(web_date, r['확인일'])

    order = {h['id']: i for i, h in enumerate(hospitals)}
    lines = [
        '// 자동 생성: data/etl/procedure_hospitals.py — 수정하지 말고 스크립트를 다시 실행',
        f'// hira: 심평원 누리집 비급여 진료비 정보 (대구 전체 내려받기, 공개기준 {BASE_MONTH})에 그 시술 가격을 공개한 병원',
        f'// web: 병원 홈페이지 진료 안내에 그 시술 이름이 있는 병원 (자동 수집 {web_date}, url = 키워드가 나온 쪽)',
        '// 둘 다 없는 시술은 목록 없음 → 화면에서 "병원 정보 준비 중"',
        f"export const PROCEDURE_HOSPITALS_DATE = '{BASE_MONTH}';",
        f"export const PROCEDURE_HOSPITALS_WEB_DATE = '{web_date}';",
        "export type ProcedureHospitalSource = { id: string; src: 'hira' } | { id: string; src: 'web'; url: string };",
        'export const PROCEDURE_HOSPITALS: Record<string, ProcedureHospitalSource[]> = {',
    ]
    for name in sorted(found, key=lambda n: -len(found[n])):
        rows = [{'id': i, **v} for i, v in sorted(found[name].items(), key=lambda kv: order[kv[0]])]
        hira = sum(1 for x in rows if x['src'] == 'hira')
        print(f'{name}: {len(rows)}곳 (심평원 {hira} · 홈페이지 {len(rows) - hira})')
        lines.append(f"  {json.dumps(name, ensure_ascii=False)}: {json.dumps(rows, ensure_ascii=False)},")
    lines.append('};')
    TS.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')

    # 챗봇용: 병원은 ykiho(= 웹 병원 id = DB hospitals.ykiho)로. 목록 없는 시술도 넣어 "자료 없음"을 말할 수 있게
    names = {h['id']: h['name'] for h in hospitals}
    procs = []
    for p in read_procedures():
        rows = sorted(found.get(p['ko'], {}).items(), key=lambda kv: order[kv[0]])
        procs.append({**p, 'hospitals': [{'ykiho': i, 'name_ko': names[i], **v} for i, v in rows]})
    CHAT_JSON.write_text(json.dumps({
        'meta': {
            'made_by': 'data/etl/procedure_hospitals.py',
            'basis': '그 시술 가격을 심평원 비급여 진료비 정보에 공개한 병원(hira) 또는 홈페이지 진료 안내에 그 시술 이름이 있는 병원(web)',
            'hira_month': BASE_MONTH, 'web_checked': web_date,
        },
        'procedures': procs,
    }, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(f'챗봇용 {CHAT_JSON.name}: 시술 {len(procs)}개 (목록 있는 것 {sum(1 for p in procs if p["hospitals"])})')


if __name__ == '__main__':
    main()
