"""병원 홈페이지 → 가격 가이드 시술별 "이 시술을 하는 병원" (출처 URL 기록)

- 입력: data/interim/시술/hospital_homepages.csv (research-data 3bff418, 메디대구 병원 161곳 중 홈페이지 94곳, homepage_source 칸에 출처)
- 방법: 홈페이지 첫 화면 + 같은 사이트 안 링크 최대 MAX_PAGES쪽을 받아 글자만 뽑고, 시술별 키워드(KEYWORDS)가 있으면 "한다"로 기록
  · 병원 진료과와 시술 진료과가 맞을 때만 (피부과·성형외과는 서로 인정) — 대학병원 질환 설명 등 엉뚱한 매칭 줄이기
  · 키워드가 처음 나온 쪽의 URL을 출처로 남김 (칸마다 출처 규칙)
- 출력: data/interim/시술/homepage_procedures.csv (병원·시술·키워드·출처URL·확인일), data/interim/시술/homepage_crawl_log.csv (병원별 받은 쪽 수·오류)
- 한계: 이미지로만 된 메뉴·자바스크립트로 그리는 사이트는 글자를 못 읽어 빠짐. 키워드가 있다고 지금 시술한다는 보장은 없음 → 화면에 "병원에 확인" 고지

실행: python -I -X utf8 data/etl/crawl_procedure_homepages.py   (표준 라이브러리만 씀)
"""
import csv
import datetime as dt
import html
import re
import ssl
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data/interim/시술/hospital_homepages.csv'
OUT = ROOT / 'data/interim/시술/homepage_procedures.csv'
LOG = ROOT / 'data/interim/시술/homepage_crawl_log.csv'

MAX_PAGES = 30
TIMEOUT = 12
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
TODAY = dt.date.today().isoformat()

# 웹 이름(procedures.ts의 ko) → (진료과, 키워드들). 공백은 무시하고 찾음
KEYWORDS = {
    # 피부과
    '보톡스': ('dermatology', ['보톡스', '보툴리눔', '보툴렉스', '제오민', '나보타']),
    '필러': ('dermatology', ['필러']),
    '윤곽주사': ('dermatology', ['윤곽주사', '브이라인주사', 'V라인주사']),
    '기미·잡티·색소침착 치료': ('dermatology', ['기미', '잡티', '색소치료', '색소침착', '피코토닝', '레이저토닝']),
    '홍조·혈관 레이저': ('dermatology', ['홍조', '혈관레이저', '브이빔', 'V-beam']),
    '여드름 진료': ('dermatology', ['여드름치료', '여드름진료', '여드름']),
    '모공·여드름 흉터 레이저': ('dermatology', ['여드름흉터', '모공치료', '프락셀', '흉터레이저']),
    '초음파·고주파 리프팅': ('dermatology', ['울쎄라', '써마지', '슈링크', '인모드', '올리지오', '초음파리프팅', '고주파리프팅', '덴서티', '티타늄리프팅']),
    '피부 탄력 관리': ('dermatology', ['탄력관리', '피부탄력', '탄력케어']),
    '피부관리': ('dermatology', ['피부관리', '아쿠아필', '필링']),
    '스킨부스터': ('dermatology', ['스킨부스터', '리쥬란', '쥬베룩', '물광주사', '엑소좀']),
    '점 제거': ('dermatology', ['점빼기', '점제거']),
    '양성 피부병변 진료': ('dermatology', ['사마귀', '쥐젖', '비립종', '한관종', '검버섯']),
    '여성·남성 레이저 제모': ('dermatology', ['제모']),
    '바디주사': ('dermatology', ['바디주사', '지방분해주사', '체형주사']),
    '비수술 체형관리': ('dermatology', ['체형관리', '쿨스컬프팅', '냉각지방']),
    # 성형외과
    '쌍꺼풀 수술': ('plastic', ['쌍꺼풀', '쌍커풀']),  # 매몰법·절개법만은 모발이식 용어와 겹쳐 뺌
    '눈매교정': ('plastic', ['눈매교정']),
    '눈밑지방 재배치': ('plastic', ['눈밑지방', '하안검']),
    '융비술': ('plastic', ['융비술', '코성형']),  # 콧대는 필러 메뉴에도 있어 뺌
    '코끝 성형': ('plastic', ['코끝']),
    '코 재수술': ('plastic', ['코재수술']),
    '광대·턱 윤곽 성형': ('plastic', ['안면윤곽', '광대축소', '사각턱수술', '턱끝수술', '양악']),  # 사각턱·턱끝만은 보톡스·필러 메뉴라 뺌
    '안면거상': ('plastic', ['안면거상', '페이스리프트']),
    '이마거상': ('plastic', ['이마거상']),
    '실리프팅': ('plastic', ['실리프팅']),
    '유방확대·축소·거상': ('plastic', ['가슴성형', '가슴확대', '유방확대', '유방축소', '가슴거상', '유방거상']),
    '지방흡입': ('plastic', ['지방흡입']),
    '지방이식': ('plastic', ['지방이식']),
    '복부성형': ('plastic', ['복부성형']),
    '바디필러 상담': ('plastic', ['바디필러']),
    '흉터 성형': ('plastic', ['흉터성형', '흉터교정']),
    '외상·화상 후 재건': ('plastic', ['화상재건', '외상재건', '재건성형']),
    '유방재건': ('plastic', ['유방재건']),
    # 안과
    '라식': ('ophthalmology', ['라식']),
    '라섹': ('ophthalmology', ['라섹']),
    '스마일': ('ophthalmology', ['스마일라식', '스마일수술', 'SMILE']),
    '안내렌즈삽입술': ('ophthalmology', ['안내렌즈', '렌즈삽입술']),
    '노안 검사·교정 상담': ('ophthalmology', ['노안']),
    '백내장 수술·인공수정체 상담': ('ophthalmology', ['백내장']),
    '안구건조증': ('ophthalmology', ['안구건조']),
    '안압·시신경·시야 검사': ('ophthalmology', ['녹내장', '시야검사']),
    '황반변성·당뇨망막병증·망막열공·망막박리 진료': ('ophthalmology', ['황반변성', '망막']),
    '사시·약시 진료': ('ophthalmology', ['사시', '약시']),
    '안검하수·눈꺼풀 이상·눈물길 질환 진료': ('ophthalmology', ['안검하수', '눈물길']),
    # 내과
    '기본·종합 건강검진': ('internal', ['건강검진', '종합검진']),
    '위·대장내시경': ('internal', ['위내시경', '대장내시경', '수면내시경']),
    '복부초음파': ('internal', ['복부초음파']),
    '고혈압·이상지질혈증·부정맥 진료': ('internal', ['고혈압', '고지혈', '이상지질']),
    '당뇨병·갑상선질환·비만·골다공증 진료': ('internal', ['당뇨', '갑상선']),
    '독감·간염·HPV 백신 접종 상담': ('internal', ['예방접종', '독감백신', '자궁경부암백신']),
    '필요에 따른 영양·수액 치료': ('internal', ['수액치료', '영양주사', '수액']),
    # 한방
    '단순추나': ('korean_medicine', ['추나']),
    '약침술': ('korean_medicine', ['약침']),
}
SKIN = {'dermatology', 'plastic'}
BOARD = re.compile(r'(?i)(bbs|board|faq|review|notice|news|blog|community|event|qna|gallery)')


def allowed(proc_dept, hosp_depts, name):
    # 성형 수술은 이름이 '피부과'인 의원에서는 인정하지 않음 (피부과 메뉴의 '눈밑지방 필러'·'사각턱 보톡스' 같은 시술이 수술로 잡히는 것 막기)
    if proc_dept == 'plastic' and '피부과' in name:
        return False
    if proc_dept in hosp_depts:
        return True
    return proc_dept == 'dermatology' and bool(SKIN & hosp_depts)


CTX = ssl.create_default_context()
LOOSE = ssl.create_default_context()
LOOSE.check_hostname = False
LOOSE.verify_mode = ssl.CERT_NONE


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ko,en;q=0.8'})
    for ctx in (CTX, LOOSE):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
                ctype = r.headers.get('Content-Type', '')
                if 'html' not in ctype and 'text' not in ctype and ctype:
                    return r.geturl(), ''
                raw = r.read(3_000_000)
                m = re.search(r'charset=([\w-]+)', ctype) or re.search(rb'charset=["\']?([\w-]+)', raw[:4000])
                enc = (m.group(1).decode() if isinstance(m.group(1), bytes) else m.group(1)) if m else 'utf-8'
                try:
                    text = raw.decode(enc, errors='replace')
                except LookupError:
                    text = raw.decode('utf-8', errors='replace')
                return r.geturl(), text
        except ssl.SSLError:
            continue
        except Exception as e:  # noqa: BLE001 — 사이트마다 오류가 달라 기록만
            if isinstance(getattr(e, 'reason', None), ssl.SSLError) and ctx is CTX:
                continue
            raise
    raise RuntimeError('ssl')


def visible(page):
    page = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', page)
    # 메뉴 이미지의 alt·title도 글자로 (이미지 메뉴 사이트)
    alts = ' '.join(re.findall(r'(?i)(?:alt|title)=["\']([^"\']{1,60})["\']', page))
    text = re.sub(r'(?s)<[^>]+>', ' ', page)
    return re.sub(r'\s+', ' ', html.unescape(text + ' ' + alts))



def has(text, kw):
    # 두 글자 키워드는 앞이 한글이면 다른 단어의 일부로 봄 ('예약시' 안의 '약시', '이노안' 등)
    if len(kw) <= 2:
        return re.search(r'(?<![가-힣])' + re.escape(kw), text) is not None
    return kw in text or kw in text.replace(' ', '')


def links(base, page):
    host = urllib.parse.urlparse(base).netloc
    out = []
    for href in re.findall(r'(?i)href=["\']([^"\'#]+)', page):
        u = urllib.parse.urljoin(base, html.unescape(href.strip()))
        p = urllib.parse.urlparse(u)
        if p.scheme in ('http', 'https') and p.netloc == host and not re.search(r'(?i)\.(jpg|jpeg|png|gif|pdf|zip|css|js|ico|svg|mp4|hwp)$', p.path):
            out.append(u.split('#')[0])
    # 진료·시술 메뉴 같은 링크 먼저
    key = re.compile(r'(?i)(sub|clinic|treat|program|menu|care|surgery|skin|eye|lift|laser|page|html|php|asp|jsp)')
    return sorted(dict.fromkeys(out), key=lambda u: 0 if key.search(u) else 1)


def crawl(h):
    depts = set(filter(None, h['depts'].split('|')))
    procs = {k: v for k, v in KEYWORDS.items() if allowed(v[0], depts, h['name_ko'])}
    found, pages, err = {}, 0, ''
    queue, seen = [h['homepage'].strip()], set()
    while queue and pages < MAX_PAGES and len(found) < len(procs):
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            final, page = fetch(url)
        except Exception as e:  # noqa: BLE001
            if pages == 0:
                err = type(e).__name__ + ': ' + str(e)[:80]
            continue
        pages += 1
        seen.add(final)
        # 프레임으로 감싼 사이트: frame src도 링크로
        page_links = links(final, page) + [urllib.parse.urljoin(final, s) for s in re.findall(r'(?i)<i?frame[^>]+src=["\']([^"\']+)', page)]
        # 게시판·후기·FAQ 글은 지나가는 말이 많아 시술 판단에 쓰지 않음 (링크는 따라감)
        if BOARD.search(final):
            queue.extend(u for u in page_links if u not in seen)
            continue
        text = visible(page)
        for name, (_, kws) in procs.items():
            if name in found:
                continue
            for kw in kws:
                if has(text, kw):
                    found[name] = (kw, final)
                    break
        queue.extend(u for u in page_links if u not in seen)
    return h, found, pages, err


def main():
    rows = [r for r in csv.DictReader(SRC.open(encoding='utf-8-sig')) if r['homepage'].startswith('http')]
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(crawl, rows))
    with OUT.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', '병원명', '시술', '키워드', '출처URL', '확인일', '출처'])
        for h, found, _, _ in results:
            for name, (kw, url) in found.items():
                w.writerow([h['id'], h['name_ko'], name, kw, url, TODAY, '병원 홈페이지 (자동 수집, 키워드 확인)'])
    with LOG.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', '병원명', '홈페이지', '받은쪽수', '찾은시술수', '오류', '확인일'])
        for h, found, pages, err in results:
            w.writerow([h['id'], h['name_ko'], h['homepage'], pages, len(found), err, TODAY])
    ok = sum(1 for _, f, p, _ in results if p)
    print(f'병원 {len(results)}곳 중 받음 {ok}곳 · 시술 찾은 병원 {sum(1 for _, f, _, _ in results if f)}곳 · 행 {sum(len(f) for _, f, _, _ in results)}')


if __name__ == '__main__':
    main()
