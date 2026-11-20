"""메디대구 인스타그램 계정 화면 만들기 (영어 통일, 2026-11-19).

만드는 것 (src/ 안에 HTML → Chrome 헤드리스로 PNG)
- profile.html      프로필 사진 1080×1080 (v3 = make_logo.py B안: M + 오른쪽 위 위치 핀 + MEDI·DAEGU)
- post_01~03.html   고정 게시물 3개 1080×1440 ("3가지 약속", 파랑 썸네일 v2)
- account.html      계정 화면 목업 1136×1560 (위 PNG를 불러옴)

색: 메디대구 웹 테마 — 파랑 #1f6feb · 연하늘 #e3edfd · 남색 #172b4d · 흰색
"""
from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, NAVY = "#1f6feb", "#e3edfd", "#172b4d"
FONT = '"Segoe UI",system-ui,sans-serif'

# ── 프로필 사진 v3 = 로고 B안 (M + 오른쪽 위 위치 핀 + MEDI·DAEGU), 시안은 make_logo.py ──
import sys  # noqa: E402
sys.path.insert(0, str(HERE))  # python -I 로 실행해도 같은 폴더의 make_logo를 찾게
from make_logo_v8 import PROFILE_ICON as PROFILE  # noqa: E402  (v8 확정: MD + 청진판 고리, 흰 배경)

# ── 게시물 12개 (영어). (위 작은 글자, 제목, 큰 기호, 아래 띠 질문) ──
POSTS = [  # 2026-11-20 팀 결정: 고정 게시물 3개 = 이용 방법 · 서비스 범위 · AI 챗봇
    ("How to use · 1 of 3", "Book a Daegu clinic<br>in 3 steps", "1", "Find → Request → Get a reply"),
    ("What we cover · 2 of 3", "From search<br>to aftercare", "2", "Find · Ask AI · Request · Aftercare"),
    ("AI chatbot · 3 of 3", "Ask our AI<br>in your language", "3", "Info only — your doctor decides"),
]


def post(top, title, mark, band, pinned):
    bg, fg, lab, mk, dot, bandbg, bandfg = (BLUE, "#fff", SKY, SKY, "#fff", SKY, NAVY) if pinned else (SKY, NAVY, BLUE, BLUE, BLUE, BLUE, "#fff")
    op = ".22" if pinned else ".12"
    return f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;box-sizing:border-box}}html,body{{width:1080px;height:1440px;overflow:hidden}}
body{{background:{bg};color:{fg};font-family:{FONT};position:relative}}
.mark{{position:absolute;right:-70px;bottom:130px;font-weight:900;font-size:900px;line-height:.8;color:{mk};opacity:{op}}}
.dot{{position:absolute;top:96px;right:96px;width:54px;height:54px;border-radius:50%;background:{dot}}}
.brand{{position:absolute;top:92px;left:96px;font-weight:700;font-size:38px}}
.top{{position:absolute;top:420px;left:96px;font-weight:700;font-size:44px;color:{lab};letter-spacing:.04em;text-transform:uppercase}}
h1{{position:absolute;top:500px;left:96px;right:96px;font-weight:900;font-size:124px;line-height:1.08;letter-spacing:-.02em}}
.band{{position:absolute;left:0;right:0;bottom:0;height:130px;background:{bandbg};color:{bandfg};font-weight:700;font-size:46px;display:flex;align-items:center;padding:0 96px}}
</style>
<div class="mark">{mark}</div><div class="dot"></div><div class="brand">MediDaegu</div>
<p class="top">{top}</p><h1>{title}</h1><div class="band">{band}</div>"""


ACCOUNT = f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;box-sizing:border-box}}
body{{width:1136px;background:#fff;color:#000;font-family:{FONT};font-size:15px}}
.bar{{height:62px;border-bottom:1px solid #dbdbdb;display:flex;align-items:center;justify-content:space-between;padding:0 130px}}
.logo{{font-family:"Segoe Script","Segoe UI",cursive;font-size:26px;font-weight:700}}
.btns{{display:flex;gap:16px;align-items:center}}.login{{background:#4f5bff;color:#fff;border-radius:8px;padding:8px 16px;font-weight:700}}.join{{color:#4f5bff}}
.head{{display:flex;gap:96px;padding:40px 130px 0 196px}}
.pic{{width:150px;height:150px;border-radius:50%;overflow:hidden;flex:none;border:1px solid #dbdbdb}}.pic img{{width:100%;height:100%}}
.info{{display:flex;flex-direction:column;gap:14px;padding-top:4px}}
.handle{{font-size:20px}}
.stats{{display:flex;gap:40px;color:#737373;font-size:16px}}.stats b{{color:#000}}
.name{{font-weight:700}}
.bio{{line-height:1.45}}
.link{{color:#00376b;font-weight:700}}
.hl{{display:flex;gap:40px;padding:44px 196px 8px}}
.h{{display:flex;flex-direction:column;align-items:center;gap:8px;font-size:12px;font-weight:600}}
.h i{{width:77px;height:77px;border-radius:50%;border:1px solid #dbdbdb;padding:3px;display:block}}
.h i b{{display:grid;place-items:center;width:100%;height:100%;border-radius:50%;background:{SKY};color:{BLUE};font-style:normal;font-size:24px}}
.tabs{{display:flex;justify-content:center;gap:180px;border-top:1px solid #dbdbdb;margin:28px 130px 0;font-size:12px;font-weight:600;letter-spacing:.08em;color:#737373}}
.tabs span{{padding:14px 0}}.tabs .on{{color:#000;border-top:1px solid #000;margin-top:-1px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;margin:0 130px 40px}}
.grid div{{aspect-ratio:3/4;overflow:hidden;position:relative}}.grid img{{width:100%;height:100%;display:block}}
.pin{{position:absolute;top:10px;right:10px;width:22px;height:22px}}
</style>
<div class="bar"><span class="logo">Instagram</span><span class="btns"><span class="login">Log in</span><span class="join">Sign up</span></span></div>
<div class="head"><div class="pic"><img src="../profile.png"></div>
<div class="info">
<div class="handle">medidaegu</div>
<div class="stats"><span><b>3</b> posts</span><span><b>—</b> followers</span><span><b>—</b> following</span></div>
<div class="name">MediDaegu | Daegu Clinic Guide</div>
<div class="bio">Book Daegu clinics — no Korean needed<br>Skin · Plastic surgery · Eye · Internal med<br>Not sponsored · No rankings · Sources shown<br>Web: EN · 繁中 · 日本語 · VI</div>
<div class="link">🔗 MediDaegu web</div>
</div></div>
<div class="hl">{''.join(f'<div class="h"><i><b>{e}</b></i>{t}</div>' for e, t in [('3','How to book'),('₩','Prices'),('?','Hours'),('+','Clinics'),('✓','Safety'),('i','FAQ')])}</div>
<div class="tabs"><span class="on">▦ POSTS</span><span>▶ REELS</span><span>◎ TAGGED</span></div>
<div class="grid">{''.join(f'<div><img src="../posts/post_{i:02d}.png">' + ('<svg class="pin" viewBox="0 0 24 24"><path fill="#fff" d="M16 3l5 5-3 1-4 4 1 5-2 2-4-4-5 5-1-1 5-5-4-4 2-2 5 1 4-4z"/></svg>' if i <= 3 else '') + '</div>' for i in range(1, 4))}</div>"""

(HERE / "profile.html").write_text(PROFILE, encoding="utf-8")
for i, p in enumerate(POSTS, 1):
    (HERE / f"post_{i:02d}.html").write_text(post(*p, pinned=i <= 3), encoding="utf-8")
(HERE / "account.html").write_text(ACCOUNT, encoding="utf-8")
print("ok")
