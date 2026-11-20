"""예상가(대구) JSON → 가격 가이드 항목별 CSV.

원본: data/raw/비급여진료/예상가_대구_20261120.json (팀원 수집, 기준일 2026-11-20)
결과: data/processed/daegu_estimate_prices.csv
- 가격 가이드 1개 항목에 예상가 시술이 여러 개면 여러 행, 없으면 빈 행 1개
- '3만원~30만원' → 30000, 300000 (원)
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data/raw/비급여진료/예상가_대구_20261120.json'
OUT = ROOT / 'data/processed/daegu_estimate_prices.csv'


def won(text):
    """'3만원' → 30000, '1200만원' → 12000000, 빈 값 → ''"""
    if not text:
        return ''
    m = re.fullmatch(r'\s*([\d,.]+)\s*만원\s*', text)
    if not m:
        raise ValueError(f'금액 형식 모름: {text!r}')
    return int(round(float(m.group(1).replace(',', '')) * 10000))


def guide_range(text):
    """'15,000~250,000' → (15000, 250000), '가격 확인 중' → ('', '')"""
    m = re.fullmatch(r'([\d,]+)~([\d,]+)', text.strip())
    if not m:
        return '', ''
    return tuple(int(g.replace(',', '')) for g in m.groups())


def main():
    data = json.loads(SRC.read_text(encoding='utf-8'))
    rows = []
    for item in data['항목']:
        g_min, g_max = guide_range(item['가격가이드_가격'])
        est = item.get('예상가 대구') or {}
        base = {
            '진료과': item['진료과'],
            '분류': item['분류'],
            '항목': item['항목'],
            '영어': item['영어'],
            '가격가이드_최소': g_min,
            '가격가이드_최대': g_max,
            '일치': est.get('일치', ''),
        }
        procs = est.get('시술') or [None]
        for p in procs:
            p = p or {}
            lo, _, hi = (p.get('가격범위') or '').partition('~')
            rows.append({
                **base,
                '예상가_시술': p.get('시술', ''),
                '예상가_최소': won(lo),
                '예상가_최대': won(hi),
                '예상가_최저참고가': won(p.get('최저참고가')),
                '평균회복기간': p.get('평균회복기간', ''),
                '평균시술시간': p.get('평균시술시간', ''),
                '비고': p.get('비고', ''),
                '기준일': data['기준일'],
                '출처': '가격 비교 플랫폼 예상가 대구 (팀원 수집, 출처 비공개)' if p else '',
            })
    assert len({r['항목'] for r in rows}) == data['항목수'], '항목 수 불일치'
    with OUT.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    matched = sum(1 for i in data['항목'] if (i.get('예상가 대구') or {}).get('시술'))
    print(f'{OUT.name}: {len(rows)}행, 항목 {data["항목수"]}개 중 예상가 연결 {matched}개')


if __name__ == '__main__':
    main()
