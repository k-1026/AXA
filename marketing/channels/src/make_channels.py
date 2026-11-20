"""메디대구 채널별 계정 화면 목업 — 유튜브 · 페이스북 · Dcard · 샤오훙수 (2026-11-20).

src/ 안에 HTML을 만들고 Chrome 헤드리스로 PNG를 찍어요 (README 참고).
이미지는 ../../instagram/profile.png(로고) · ../../thumbnails/*.png(썸네일 v2) · ../../instagram/posts/*.png를 다시 써요.
실제 서비스 화면을 그대로 베끼지 않고, 구조(프로필·소개·게시물 목록)만 비슷하게 그린 예시예요.
"""
from pathlib import Path

HERE = Path(__file__).parent
BLUE, SKY, NAVY = "#1f6feb", "#e3edfd", "#172b4d"
FONT = '"Segoe UI","Microsoft JhengHei",system-ui,sans-serif'
BFONT = "'Segoe UI','Microsoft JhengHei',sans-serif"  # style 속성 안에서 쓰는 글꼴 (작은따옴표)
LOGO = "../../instagram/profile.png"
TH = "../../thumbnails/"
PO = "../../instagram/posts/"


def banner(w, h, text, sub):
    """채널 배너·커버: 파랑 바탕 + 큰 글자 + 브랜드 점 + 연하늘 큰 3."""
    return f"""<div style="position:relative;width:{w}px;height:{h}px;background:{BLUE};overflow:hidden;border-radius:12px;color:#fff">
<div style="position:absolute;right:-20px;bottom:-{int(h*.35)}px;font:900 {int(h*1.3)}px 'Segoe UI';color:{SKY};opacity:.2;line-height:1">3</div>
<div style="position:absolute;top:{int(h*.12)}px;right:{int(h*.12)}px;width:{int(h*.09)}px;height:{int(h*.09)}px;border-radius:50%;background:#fff"></div>
<div style="position:absolute;left:{int(h*.16)}px;top:{int(h*.3)}px;font:900 {int(h*.17)}px {BFONT}">{text}</div>
<div style="position:absolute;left:{int(h*.16)}px;top:{int(h*.56)}px;font:700 {int(h*.08)}px {BFONT};background:{SKY};color:{NAVY};padding:{int(h*.025)}px {int(h*.06)}px;border-radius:999px">{sub}</div>
</div>"""


# ── 유튜브 채널 (영어, 쇼츠 탭) ──
# 2026-11-20 팀 결정: 모든 채널에 고정 게시물 3개("3가지 약속")만 남김
PROMISES = [  # 고정 3개: 이용 방법 · 서비스 범위 · AI 챗봇 (영어 / 번체 / 베트남어 / 일본어)
    ("post_01.png", "How to use · Book a Daegu clinic in 3 steps: find, request, get a reply.", "使用方法：3步驟預約大邱診所", "Cách dùng: đặt lịch phòng khám ở Daegu trong 3 bước.", "使い方：大邱のクリニックを3ステップで予約（探す→相談を送る→返信を確認）"),
    ("post_02.png", "What we cover · From search to aftercare: find clinics, ask our AI, send a consult request, aftercare. We don't diagnose, rank clinics or offer discounts.", "服務範圍：從找診所到術後照護", "Phạm vi: từ tìm phòng khám đến chăm sóc sau điều trị. Không chẩn đoán, không xếp hạng, không giảm giá.", "サービス範囲：クリニック探しからアフターケアまで。診断・ランキング・割引はしません。"),
    ("post_03.png", "AI chatbot · Ask about clinics, prices and interpretation in your language. Info only — your doctor decides.", "AI聊天機器人：用你的語言提問", "Chatbot AI: hỏi về phòng khám, giá và phiên dịch bằng ngôn ngữ của bạn. Chỉ cung cấp thông tin.", "AIチャットボット：クリニック・料金・通訳について母国語で質問。情報提供のみで、診療は医師が判断します。"),
]
YOUTUBE = f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;box-sizing:border-box}}body{{width:1280px;background:#fff;color:#0f0f0f;font-family:{FONT};padding:0 0 40px}}
.top{{height:56px;display:flex;align-items:center;gap:16px;padding:0 24px;border-bottom:1px solid #eee}}
.yt{{display:flex;align-items:center;gap:6px;font-weight:700;font-size:20px}}.yt b{{background:#e00;color:#fff;border-radius:6px;padding:0 7px;font-size:13px}}
.search{{flex:1;max-width:560px;margin:0 auto;border:1px solid #ccc;border-radius:40px;height:40px;padding:0 18px;display:flex;align-items:center;color:#888}}
.wrap{{padding:16px 100px}}
.head{{display:flex;gap:24px;align-items:center;margin-top:20px}}
.head img{{width:160px;height:160px;border-radius:50%;border:1px solid #e5e5e5}}
h1{{font-size:36px;font-weight:700}}.meta{{color:#606060;font-size:14px;margin-top:6px}}.desc{{color:#606060;font-size:14px;margin-top:8px}}
.link{{color:#065fd4;font-size:14px;margin-top:6px}}.sub{{display:inline-block;margin-top:12px;background:#0f0f0f;color:#fff;border-radius:20px;padding:9px 16px;font-weight:600;font-size:14px}}
.tabs{{display:flex;gap:28px;border-bottom:1px solid #e5e5e5;margin-top:24px;font-weight:600;color:#606060}}.tabs span{{padding:12px 0}}.tabs .on{{color:#0f0f0f;border-bottom:2px solid #0f0f0f}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:20px}}
.card img{{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:12px;display:block}}
.card p{{font-size:15px;font-weight:600;margin-top:8px;line-height:1.3}}.card span{{color:#606060;font-size:13px}}
</style>
<div class="top"><span class="yt"><b>▶</b>YouTube</span><span class="search">Search</span></div>
<div class="wrap">
{banner(1080, 178, "Book Daegu clinics — no Korean needed", "Dermatology · Plastic surgery · Eye · Internal medicine")}
<div class="head"><img src="{LOGO}"><div>
<h1>MediDaegu</h1>
<div class="meta">@medidaegu · — subscribers · 3 posts</div>
<div class="desc">Short guides to booking clinics in Daegu, Korea. Not sponsored · No rankings · Sources shown</div>
<div class="link">MediDaegu web (link TBD) and 2 more links</div>
<span class="sub">Subscribe</span></div></div>
<div class="tabs"><span>Home</span><span>Videos</span><span>Shorts</span><span>Playlists</span><span class="on">Posts</span></div>
<div class="grid" style="grid-template-columns:repeat(3,1fr)">{''.join(f'<div class="card"><img src="{PO}{f}" style="aspect-ratio:3/4"><p>📌 {en}</p><p style="font-weight:400;color:#606060;font-size:13px;margin-top:4px">[JA] {ja}</p><span>Pinned · — likes</span></div>' for f, en, zh, vi, ja in PROMISES)}</div>
</div>"""

# ── 페이스북 페이지 (영어 페이지 + 베트남어 게시물) ──
FACEBOOK = f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;box-sizing:border-box}}body{{width:1100px;background:#f0f2f5;color:#050505;font-family:{FONT};padding-bottom:30px}}
.bar{{height:56px;background:#fff;display:flex;align-items:center;padding:0 16px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
.fb{{width:40px;height:40px;border-radius:50%;background:#0866ff;color:#fff;font:900 26px 'Segoe UI';display:grid;place-items:center}}
.cover{{background:#fff;padding:0 70px 0}}
.head{{display:flex;gap:20px;align-items:flex-end;padding:0 30px;margin-top:-50px}}
.head img{{width:168px;height:168px;border-radius:50%;border:4px solid #fff;box-shadow:0 0 0 1px #dddfe2;position:relative}}
.head h1{{font-size:32px;font-weight:700}}.head .m{{color:#65676b;font-weight:600;margin:4px 0 16px}}
.btns{{margin-left:auto;display:flex;gap:8px;margin-bottom:16px}}.btn{{background:#0866ff;color:#fff;border-radius:6px;padding:8px 14px;font-weight:600}}.btn.g{{background:#e4e6eb;color:#050505}}
.tabs{{display:flex;gap:26px;border-top:1px solid #ddd;margin:16px 30px 0;padding:14px 0;color:#65676b;font-weight:600}}.tabs .on{{color:#0866ff}}
.body{{display:grid;grid-template-columns:360px 1fr;gap:16px;padding:16px 70px}}
.box{{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
.box h2{{font-size:20px;margin-bottom:12px}}.box p{{font-size:15px;line-height:1.45;margin-bottom:8px}}
.post .who{{display:flex;gap:10px;align-items:center;margin-bottom:10px}}.post .who img{{width:40px;height:40px;border-radius:50%;border:1px solid #dddfe2}}
.post .who b{{display:block}}.post .who span{{color:#65676b;font-size:13px}}
.post .txt{{font-size:15px;line-height:1.45;margin-bottom:10px}}.post .pic{{width:100%;border-radius:4px;display:block}}
.post .act{{display:flex;justify-content:space-around;color:#65676b;font-weight:600;border-top:1px solid #ddd;margin-top:10px;padding-top:8px}}
</style>
<div class="bar"><span class="fb">f</span></div>
<div class="cover">{banner(960, 280, "No Korean? Still book.", "Daegu clinics · EN · 繁中 · Tiếng Việt")}
<div class="head"><img src="{LOGO}"><div><h1>MediDaegu</h1><div class="m">— followers · Medical tourism information</div></div>
<div class="btns"><span class="btn">Learn more</span><span class="btn g">Message</span></div></div>
<div class="tabs"><span class="on">Posts</span><span>About</span><span>Photos</span><span>Reels</span></div></div>
<div class="body">
<div class="box"><h2>Intro</h2>
<p>Short guides to booking clinics in Daegu, Korea — no Korean needed.</p>
<p>Hướng dẫn đặt lịch phòng khám tại Daegu, không cần biết tiếng Hàn.</p>
<p>Not sponsored · No rankings · Sources shown</p>
<p style="color:#65676b">🔗 MediDaegu web (link TBD)</p></div>
<div style="display:flex;flex-direction:column;gap:16px">
{''.join(f'<div class="box post"><div class="who"><img src="{LOGO}"><div><b>MediDaegu</b><span>📌 Pinned · 🌐</span></div></div><div class="txt">{en}<br><span style="color:#65676b">[VI] {vi}</span></div><img class="pic" src="{PO}{f}" style="width:56%;margin:0 auto"><div class="act"><span>👍 Like</span><span>💬 Comment</span><span>↗ Share</span></div></div>' for f, en, zh, vi, ja in PROMISES)}
</div></div>"""

# ── Dcard 브랜드 계정 (번체 중국어) ──
DCARD_POSTS = [
    ("醫美板", "#分享 MediDaegu 使用方法｜3步驟預約大邱診所", "找診所 → 送出諮詢需求 → 看診所回覆狀態，不會韓文也OK。", "post_01.png"),
    ("醫美板", "#分享 服務範圍｜從找診所到術後照護", "找診所・問AI・送出諮詢・術後照護（回國後也能問、確認收據金額）。不做診斷、不排名、不給折扣。", "post_02.png"),
    ("韓國板", "#分享 AI聊天機器人｜用你的語言問大邱看診", "診所資訊・價格・口譯都能問；只提供資訊，診療由醫師判斷。", "post_03.png"),
]
DCARD = f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;box-sizing:border-box}}body{{width:1000px;background:#f2f3f4;color:#000;font-family:{FONT};padding-bottom:30px}}
.bar{{height:52px;background:#006aa6;color:#fff;display:flex;align-items:center;padding:0 24px;font-weight:700;font-size:20px;letter-spacing:.02em}}
.page{{width:728px;margin:20px auto;background:#fff;border-radius:6px;overflow:hidden}}
.prof{{padding:28px;display:flex;gap:20px;align-items:center;border-bottom:1px solid #e9e9e9}}
.prof img{{width:96px;height:96px;border-radius:50%;border:1px solid #e9e9e9}}
.prof h1{{font-size:26px;font-weight:700;display:flex;align-items:center;gap:8px}}
.badge{{font-size:13px;font-weight:600;background:{SKY};color:{BLUE};border-radius:4px;padding:2px 8px}}
.prof .b{{color:rgba(0,0,0,.6);margin-top:6px;font-size:15px;line-height:1.5}}.prof .f{{color:rgba(0,0,0,.5);font-size:14px;margin-top:6px}}
.follow{{margin-left:auto;align-self:flex-start;border:1px solid #006aa6;color:#006aa6;border-radius:4px;padding:6px 16px;font-weight:600}}
.tabs{{display:flex;gap:28px;padding:0 28px;border-bottom:1px solid #e9e9e9;color:rgba(0,0,0,.5);font-weight:600}}.tabs span{{padding:14px 0}}.tabs .on{{color:#000;border-bottom:2px solid #006aa6}}
.post{{display:flex;gap:16px;padding:20px 28px;border-bottom:1px solid #e9e9e9}}
.post .t{{flex:1;min-width:0}}.post .board{{font-size:13px;color:rgba(0,0,0,.5)}}
.post h2{{font-size:18px;font-weight:700;margin:6px 0}}.post p{{font-size:15px;color:rgba(0,0,0,.6);line-height:1.5}}
.post .m{{font-size:13px;color:rgba(0,0,0,.4);margin-top:8px}}
.post img{{width:84px;height:84px;object-fit:cover;object-position:top;border-radius:6px;flex:none}}
</style>
<div class="bar">Dcard</div>
<div class="page">
<div class="prof"><img src="{LOGO}"><div>
<h1>MediDaegu <span class="badge">品牌帳號</span></h1>
<div class="b">大邱看診預約指南｜不會韓文也OK<br>非業配・不推薦特定診所・資料附來源</div>
<div class="f">— 位粉絲 · 3 篇文章</div></div><span class="follow">追蹤</span></div>
<div class="tabs"><span class="on">文章</span><span>關於</span></div>
{''.join(f'<div class="post"><div class="t"><div class="board">{b} · MediDaegu</div><h2>{h}</h2><p>{p}</p><div class="m">♡ — · 💬 — · 收藏 —</div></div><img src="{PO}{img}" style="object-position:left top"></div>' for b, h, p, img in DCARD_POSTS)}
</div>"""

# ── 샤오훙수 (중국 본토, 간체 중국어) — 2026-11-20 팀 결정으로 추가 ──
XHS_NOTES = [
    ("post_01.png", "使用方法：3步预约大邱诊所", "找诊所 → 提交咨询 → 查看回复"),
    ("post_02.png", "服务范围：从找诊所到术后照护", "找诊所・问AI・咨询・术后照护"),
    ("post_03.png", "AI聊天机器人：用你的语言提问", "只提供信息，诊疗由医生判断"),
]
XHS = f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;box-sizing:border-box}}body{{width:900px;background:#fff;color:#333;font-family:"Microsoft YaHei","Segoe UI",sans-serif;padding-bottom:30px}}
.bar{{height:56px;display:flex;align-items:center;padding:0 24px;border-bottom:1px solid #eee}}
.logo{{background:#ff2442;color:#fff;font-weight:700;border-radius:8px;padding:4px 10px;font-size:18px}}
.prof{{display:flex;gap:28px;padding:32px 48px 20px;align-items:center}}
.prof img{{width:120px;height:120px;border-radius:50%;border:1px solid #eee}}
.prof h1{{font-size:26px;color:#111}}.id{{color:#999;font-size:13px;margin-top:6px}}
.bio{{font-size:14px;line-height:1.6;margin-top:10px;color:#333}}
.st{{display:flex;gap:22px;margin-top:12px;font-size:14px;color:#666}}.st b{{color:#111;margin-right:4px}}
.tags{{display:flex;gap:8px;margin-top:10px}}.tags span{{background:#f5f5f5;border-radius:999px;padding:3px 10px;font-size:12px;color:#666}}
.btn{{margin-left:auto;align-self:flex-start;background:#ff2442;color:#fff;border-radius:999px;padding:8px 26px;font-weight:600}}
.tabs{{display:flex;justify-content:center;gap:48px;border-bottom:1px solid #eee;font-size:16px;color:#999}}.tabs span{{padding:12px 0}}.tabs .on{{color:#111;font-weight:700;border-bottom:2px solid #ff2442}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;padding:20px 48px}}
.note img{{width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:12px;display:block}}
.note p{{font-size:14px;font-weight:600;color:#111;margin-top:8px;line-height:1.4}}
.note .m{{display:flex;justify-content:space-between;align-items:center;margin-top:6px;font-size:12px;color:#999}}
.note .m i{{display:inline-flex;align-items:center;gap:4px;font-style:normal}}
.note .m img{{width:18px;height:18px;border-radius:50%;aspect-ratio:auto;border:1px solid #eee}}
.top{{background:#ff2442;color:#fff;font-size:11px;border-radius:4px;padding:1px 6px;margin-right:4px}}
</style>
<div class="bar"><span class="logo">小红书</span></div>
<div class="prof"><img src="{LOGO}"><div>
<h1>MediDaegu</h1>
<div class="id">小红书号：medidaegu（待确认） · IP属地：韩国</div>
<div class="bio">大邱看诊预约指南｜不会韩语也OK<br>非广告・不推荐特定诊所・资料附来源<br>网页：简体中文・人民币换算</div>
<div class="tags"><span>皮肤科</span><span>整形外科</span><span>眼科</span><span>内科</span></div>
<div class="st"><span><b>—</b>关注</span><span><b>—</b>粉丝</span><span><b>—</b>获赞与收藏</span></div>
</div><span class="btn">关注</span></div>
<div class="tabs"><span class="on">笔记</span><span>收藏</span><span>赞过</span></div>
<div class="grid">{''.join(f'<div class="note"><img src="{PO}{f}"><p><span class="top">置顶</span>{t}</p><div class="m"><i><img src="{LOGO}">MediDaegu</i><span>♡ —</span></div></div>' for f, t, d in XHS_NOTES)}</div>"""

for name, html in [("youtube", YOUTUBE), ("facebook", FACEBOOK), ("dcard", DCARD), ("xiaohongshu", XHS)]:
    (HERE / f"{name}.html").write_text(html, encoding="utf-8")
print("ok")
