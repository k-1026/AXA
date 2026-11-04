"""폐업 교차검증 표본 점검 시트 만들기.

판정이 맞는지 보려고 '정상' 중 무작위 30곳 + '폐업' 전부를 뽑아 지도로 직접 확인한다.
입력: data/processed/daegu_hospital_status.csv (verify_hospital_status.py 결과)
출력: data/interim/영업정보/hospital_status_sample.csv (빈칸: 지도결과·출처·확인일·일치)

실행: .venv/Scripts/python.exe data/etl/sample_hospital_status.py
같은 시드라 다시 돌려도 같은 표본이 나옴. 이미 채운 칸은 ykiho 기준으로 유지.
"""
import csv
import html
import random
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / 'data/processed/daegu_hospital_status.csv'
OUT = ROOT / 'data/interim/영업정보/hospital_status_sample.csv'
SEED = 20261102
N_OPEN = 30
FILL = ['지도결과', '출처', '확인일', '일치']


def main():
    with STATUS.open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    open_rows = sorted((r for r in rows if r['verdict'] == '정상'), key=lambda r: r['ykiho'])
    sample = random.Random(SEED).sample(open_rows, N_OPEN)
    sample += [r for r in rows if r['verdict'] == '폐업']

    done = {}
    if OUT.exists():
        with OUT.open(encoding='utf-8-sig') as f:
            done = {r['ykiho']: r for r in csv.DictReader(f)}

    out = []
    for r in sample:
        name = html.unescape(r['yadmNm'])
        query = f"{name} {r['sgguCdNm'].replace('대구', '대구 ')}"
        prev = done.get(r['ykiho'], {})
        out.append({
            'ykiho': r['ykiho'], '판정': r['verdict'], '이름': name, '종별': r['clCdNm'],
            '구': r['sgguCdNm'], '주소': html.unescape(r['addr']), '웹대상': r['target_4dept'],
            '네이버지도': 'https://map.naver.com/p/search/' + urllib.parse.quote(query),
            **{k: prev.get(k, '') for k in FILL},
        })

    with OUT.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print('표본', OUT.relative_to(ROOT), len(out), '곳 (정상', N_OPEN, '+ 폐업', len(out) - N_OPEN, ')')

    checked = [r for r in out if r['일치']]
    if checked:
        ok = sum(r['일치'] == 'Y' for r in checked)
        print(f'확인 {len(checked)}곳 중 일치 {ok}곳')


if __name__ == '__main__':
    main()
