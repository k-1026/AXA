"""대구 병원 폐업·미존재 교차검증.

기준: data/raw/영업정보/daegu_hospitals.json (심평원 getHospBasisList, 2026-10-28 수집)
출처 A: 심평원 getHospBasisList 최신 재조회 → raw/영업정보/daegu_hospitals_<날짜>.json
출처 B: 행정안전부 건강_병원·건강_의원 조회서비스(인허가, 영업상태) → raw/영업정보/mois_<hospitals|clinics>_<날짜>.json
        (data.go.kr 활용신청이 된 키가 있어야 함. 없으면 건너뜀)
출처 C: 직접 확인 시트 interim/영업정보/hospital_status_manual.csv (빈칸만, 칸마다 출처)
결과: data/processed/daegu_hospital_status.csv

실행: .venv/Scripts/python.exe data/etl/verify_hospital_status.py [--skip-fetch]
"""
import csv
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/영업정보'
TODAY = date.today().strftime('%Y%m%d')

HIRA_URL = 'http://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList'
MOIS_URL = 'https://apis.data.go.kr/1741000/{ep}/info'
# 대구 개방자치단체코드(시 본청 + 8개 구·군). 군위군(2023 편입)은 의원 API의 주소 필터로 보완
DAEGU_ATMY = ['6270000', '3410000', '3420000', '3430000', '3440000',
              '3450000', '3460000', '3470000', '3480000']


def service_key():
    for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        if line.startswith('DATA_GO_KR_SERVICE_KEY='):
            return line.split('=', 1)[1].strip()
    sys.exit('.env에 DATA_GO_KR_SERVICE_KEY 없음')


def call(url, params):
    key = service_key()
    key = key if '%' in key else urllib.parse.quote(key, safe='')
    q = 'serviceKey=' + key + '&' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url + '?' + q, timeout=120) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_hira():
    items, page = [], 1
    while True:
        body = call(HIRA_URL, {'sidoCd': '230000', 'pageNo': page,
                               'numOfRows': 1000, '_type': 'json'})['response']['body']
        got = body['items']['item'] if body['items'] else []
        items += got if isinstance(got, list) else [got]
        if len(items) >= body['totalCount'] or not got:
            break
        page += 1
    out = {'meta': {'source': '건강보험심사평가원_병원정보서비스 getHospBasisList',
                    'url': 'https://www.data.go.kr/data/15001698/openapi.do',
                    'sidoCd': '230000', 'totalCount': body['totalCount'],
                    'fetchedAt': datetime.now(timezone.utc).isoformat()},
           'items': items}
    path = RAW / f'daegu_hospitals_{TODAY}.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('심평원 최신', len(items), '→', path.name)


def fetch_mois():
    for ep, conds in [('hospitals', [{'cond[OPN_ATMY_GRP_CD::EQ]': c} for c in DAEGU_ATMY]),
                      ('clinics', [{'cond[ROAD_NM_ADDR::LIKE]': '대구광역시'}])]:
        items = []
        try:
            for cond in conds:
                page = 1
                while True:
                    res = call(MOIS_URL.format(ep=ep), {'pageNo': page, 'numOfRows': 100,
                                                        'returnType': 'json', **cond})
                    body = res['response']['body']
                    got = body['items']['item'] if body.get('items') else []
                    got = got if isinstance(got, list) else [got]
                    items += got
                    if page * 100 >= int(body['totalCount']) or not got:
                        break
                    page += 1
        except Exception as e:  # 활용신청 전이면 403 SERVICE_KEY_IS_NOT_REGISTERED_ERROR
            print(f'행안부 {ep} 건너뜀: {e}')
            continue
        out = {'meta': {'source': f'행정안전부_건강_{ep} 조회서비스', 'fetchedAt':
                        datetime.now(timezone.utc).isoformat(), 'count': len(items)},
               'items': items}
        (RAW / f'mois_{ep}_{TODAY}.json').write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
        print('행안부', ep, len(items))


def latest(pattern):
    files = sorted(RAW.glob(pattern))
    return json.loads(files[-1].read_text(encoding='utf-8')) if files else None


def norm_name(s):
    # 심평원은 '&amp;', 행안부는 '&' → 풀고 비교
    return re.sub(r'[\s()（）·.\-]', '', html.unescape(s or ''))


def norm_addr(s):
    # "대구광역시 중구 동덕로 130, (삼덕동2가 …)" → "중구동덕로130"
    s = html.unescape(s or '').split(',')[0].split('(')[0]
    s = s.replace('대구광역시', '').replace('대구', '')
    return re.sub(r'\s', '', s)


def mois_index():
    """행안부 인허가를 (이름) → 레코드 목록으로. 필드명은 첫 수집 후 확인해 맞출 것."""
    idx = {}
    for ep in ['hospitals', 'clinics']:
        data = latest(f'mois_{ep}_*.json')
        if not data:
            continue
        for it in data['items']:
            name = it.get('BPLC_NM')
            if name is None:
                sys.exit(f'행안부 {ep} 필드명 확인 필요: {list(it)[:20]}')
            idx.setdefault(norm_name(name), []).append(it)
    return idx


def mois_status(row, idx):
    cands = idx.get(norm_name(row['yadmNm']), [])
    if not cands:
        return '', '', ''
    addr = norm_addr(row['addr'])
    same = [c for c in cands if norm_addr(c.get('ROAD_NM_ADDR', '')) == addr] or cands
    # 같은 이름이 여러 개면 영업 중인 것을 우선
    same.sort(key=lambda c: str(c.get('SALS_STTS_NM', c.get('SALS_STTS_CD', ''))) != '영업/정상')
    c = same[0]
    return (str(c.get('SALS_STTS_NM', c.get('SALS_STTS_CD', ''))),
            str(c.get('CLSBIZ_YMD', '')), str(c.get('LCPMT_YMD', '')))


def main():
    if '--skip-fetch' not in sys.argv:
        fetch_hira()
        fetch_mois()

    base = json.loads((RAW / 'daegu_hospitals.json').read_text(encoding='utf-8'))
    new = latest('daegu_hospitals_2*.json')
    new_items = {it['ykiho']: it for it in new['items']}
    new_date = new['meta']['fetchedAt'][:10]
    idx = mois_index()
    manual_path = ROOT / 'data/interim/영업정보/hospital_status_manual.csv'
    manual = {}
    if manual_path.exists():
        with manual_path.open(encoding='utf-8-sig') as f:
            manual = {r['ykiho']: r for r in csv.DictReader(f)}

    # 웹 대상 4개 진료과 (apps/web-platform/scripts/build-hospitals.mjs와 같은 기준)
    with (ROOT / 'data/interim/영업정보/daegu_hospital_hours.csv').open(encoding='utf-8-sig') as f:
        hours = {r['ykiho']: r for r in csv.DictReader(f)}

    def target(b):
        h = hours.get(b['ykiho'], {})
        cl, name = b['clCdNm'], b['yadmNm']
        medical = not cl.startswith('치과') and not cl.startswith('한')
        return 'Y' if (h.get('has_dermatology') == 'Y' or h.get('has_plastic_surgery') == 'Y'
                       or (medical and '내과' in name) or cl.startswith('치과')) else 'N'

    rows = []
    for b in base['items']:
        k = b['ykiho']
        n = new_items.get(k)
        hira = '있음' if n else '없음'
        changes = []
        if n:
            for f, label in [('yadmNm', '이름'), ('addr', '주소'), ('telno', '전화')]:
                # 원본마다 &amp; 이스케이프가 달라서 풀고 비교
                if html.unescape(str(n.get(f, ''))) != html.unescape(str(b.get(f, ''))):
                    changes.append(label)
        m_stat, m_close, m_open = mois_status(b, idx) if idx else ('', '', '')
        man = manual.get(k, {})
        no_xy = not (b.get('XPos') and b.get('YPos'))

        # 판정: 독립 출처 2개가 같은 방향일 때만 정상/폐업, 아니면 미확인
        closed_votes = [hira == '없음', m_stat.startswith('폐업'), man.get('판정') == '폐업']
        open_votes = [hira == '있음', m_stat.startswith('영업'), man.get('판정') == '정상']
        if sum(closed_votes) >= 2:
            verdict = '폐업'
        elif sum(open_votes) >= 2:
            verdict = '정상'
        else:
            verdict = '미확인'
        reason = []
        if hira == '없음':
            reason.append(f'심평원 {new_date} 목록에서 빠짐')
        if changes:
            reason.append('심평원 변경: ' + '·'.join(changes))
        if m_stat:
            reason.append(f'행안부 영업상태 {m_stat}' + (f' 폐업일 {m_close}' if m_close else ''))
        elif idx:
            reason.append('행안부 인허가에서 이름 매칭 안 됨')
        if man.get('근거'):
            reason.append(man['근거'])
        if no_xy:
            reason.append('좌표 없음')
        rows.append({
            'ykiho': k, 'yadmNm': b['yadmNm'], 'clCdNm': b['clCdNm'],
            'sgguCdNm': b['sgguCdNm'], 'addr': html.unescape(b['addr']), 'estbDd': b['estbDd'],
            'target_4dept': target(b),
            'closure_candidate': 'Y' if hira == '없음' or m_stat.startswith('폐업') else 'N',
            'hira_20261028': '있음', f'hira_{new_date.replace("-", "")}': hira,
            'mois_status': m_stat, 'mois_close_date': m_close,
            'manual_verdict': man.get('판정', ''), 'manual_source': man.get('출처', ''),
            'manual_checked': man.get('확인일', ''),
            'verdict': verdict, 'reason': ' / '.join(reason),
        })

    out = ROOT / 'data/processed/daegu_hospital_status.csv'
    with out.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    added = [it for k, it in new_items.items() if k not in {b['ykiho'] for b in base['items']}]
    print('결과', out.relative_to(ROOT), len(rows), '행 |',
          {v: sum(r['verdict'] == v for r in rows) for v in ['정상', '폐업', '미확인']},
          '| 심평원에서 빠짐', sum(r[f'hira_{new_date.replace("-", "")}'] == '없음' for r in rows),
          '| 새로 생김', len(added))
    for it in added:
        print('  신규', it['yadmNm'], it['clCdNm'], it['estbDd'])


if __name__ == '__main__':
    main()
