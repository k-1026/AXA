// 병원 대시보드 화면 동작 (예전 dashboard/대시보드.html의 <script>를 그대로 옮김)
// DashboardPage가 markup.html을 host(.md-dashboard)에 넣은 뒤 startDashboard를 부르고, 화면을 떠나면 돌려준 정리 함수를 부른다
// 문서 전체 id(document.getElementById)로 찾으므로 한 화면에 하나만 띄운다
import { API_BASE } from '../../components/api';
import { clearStaffToken, readStaffToken, saveStaffToken } from '../../features/staff/staffSession';

export function startDashboard(host, { onLeave }) {
  const cleanups = [];
  const timers = [];
  const won = (n) => '₩' + n.toLocaleString('ko-KR');
  const state = { ac: true, tier: 'premium' };
  function show(t) {
    document.querySelectorAll('main > section').forEach(s => s.classList.toggle('hidden', s.id !== t));
    document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
    window.scrollTo(0, 0);
  }
  document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => { location.hash = b.dataset.t; });
  const fromHash = () => { const t = (location.hash || '#home').slice(1); show(document.getElementById(t) ? t : 'home'); };
  window.addEventListener('hashchange', fromHash);
  cleanups.push(() => window.removeEventListener('hashchange', fromHash));

  function subCost() {
    // 요금 v4: 기본 회원 무료 + 13% / 프리미엄 연 ₩1,800,000(월 환산 ₩150,000) + 8%
    if (state.tier === 'basic') return { cost: 0, label: '기본 회원 (회원비 없음)' };
    return { cost: 150000, label: '프리미엄 회원비 (연 ₩1,800,000의 월 환산)' };
  }
  function render() {
    const revenue = 32130000, rate = state.tier === 'basic' ? 0.13 : 0.08, pct = Math.round(rate * 100);
    const commission = Math.round(revenue * rate), sub = subCost(), total = commission + sub.cost;
    const tierName = state.tier === 'basic' ? '기본' : '프리미엄';
    const set = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    const ratio = (total / revenue * 100).toFixed(1) + '%';
    set('homeRatio', ratio); set('ratioAll', ratio);
    set('homeCom', won(commission)); set('homeComLabel', `체결 진료 수수료 (${tierName} ${pct}%)`);
    set('sumCom', won(commission)); set('sumComLabel', `체결 진료 수수료 (확인 완료 21건 · 진료비 ₩32,130,000 × ${pct}%)`);
    set('rcCom', won(commission)); set('rateNow', `${pct}% (${tierName})`);
    document.getElementById('ratioBar').style.width = (total / revenue * 100 / 30 * 100).toFixed(0) + '%';
    set('homeCost', won(total)); set('homeCost2', won(total)); set('homePer', won(Math.round(total / 24)));
    document.getElementById('homeBar').style.width = Math.min(100, total / 4800000 * 100).toFixed(0) + '%';
    set('sumSub', won(sub.cost)); set('sumSubLabel', sub.label); set('homeSub', won(sub.cost));
    set('homeSubLabel', state.tier === 'basic' ? '(기본 회원)' : '(프리미엄 · 월 환산)');
    document.querySelectorAll('#subPlans .plan').forEach((x) => x.classList.toggle('on', x.dataset.tier === state.tier));
    set('sumTotal', won(total)); set('homeTotal', won(total));
    set('acIncluded', '19건 (기본 30건)');
    set('acExtra', '0건');
    set('acPlanName', state.tier === 'basic' ? '기본 회원에 포함' : '프리미엄 회원에 포함');
    set('setAc', state.ac ? '지원' : '미지원');
    document.getElementById('acBody').classList.toggle('hidden', !state.ac);
    document.getElementById('acOff').classList.toggle('hidden', state.ac);
    const h = document.getElementById('hdrAftercare');
    h.textContent = state.ac ? '사후관리 지원' : '사후관리 미지원'; h.className = 'badge' + (state.ac ? '' : ' gray');
    document.getElementById('acText').innerHTML = state.ac
      ? '환자 사이트 병원 목록의 <b>"사후관리 지원"</b> 필터에 이 병원이 나와요.'
      : '"사후관리 지원" 필터로 찾을 때 이 병원은 <b>빠져요</b>. 기본 목록에는 그대로 보여요.';
  }
  function bindSwitch(id, fn) {
    const el = document.getElementById(id);
    el.querySelectorAll('button').forEach(b => b.onclick = () => {
      el.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); fn(b.dataset.v); render();
    });
  }
  bindSwitch('acSwitch', v => state.ac = v === 'on');
  document.querySelectorAll('#subPlans .plan').forEach(p => p.onclick = () => { state.tier = p.dataset.tier; render(); });

  document.querySelectorAll('.spark').forEach(el => {
    const s = el.dataset.s.split(',').map(Number), m = Math.max(...s);
    el.innerHTML = s.map(v => `<i style="height:${Math.round(v / m * 100)}%"></i>`).join('');
  });
  const now = [52,61,48,70,66,90,95,58,63,72,69,84,101,97,76,88], prev = [44,50,47,55,60,71,78,49,52,58,61,66,80,79,62,70];
  const mx = Math.max(...now, ...prev);
  document.getElementById('visits').innerHTML = now.map((v, i) =>
    `<div class="p" title="지난달 ${prev[i]}" style="height:${Math.round(prev[i] / mx * 100)}%"></div><div title="이번 달 ${v}" style="height:${Math.round(v / mx * 100)}%"></div>`).join('');
  const days = ['월','화','수','목','금','토','일'], slots = ['09시','12시','15시','18시','21시'];
  const heat = [[2,3,3,3,4,6,5],[3,3,4,3,4,7,6],[3,4,3,4,5,8,6],[6,6,7,6,8,9,7],[7,8,7,8,9,8,6]];
  let hh = '<span></span>' + days.map(d => `<span>${d}</span>`).join('');
  slots.forEach((s, r) => { hh += `<span>${s}</span>` + heat[r].map(v => `<i title="${s} ${v}" style="opacity:${(v / 9).toFixed(2)}"></i>`).join(''); });
  document.getElementById('heat').innerHTML = hh;

  // 채팅 (예시 데이터 · 가상 환자)
  const CHATS = {
    booking: [
      { id: 'R-1043', who: '대만 · 번체', unread: 2, title: '레이저 토닝 상담', sub: '희망일 11/21 오전 · 11/22 오후 · 체류 11/20~24',
        sum: '대만, 30대 여성(본인 입력). 레이저 토닝 상담 희망. 빠진 정보: 연락받을 메신저', tags: ['레이저 토닝', '희망일 2개', '비자 불필요'],
        msgs: [
          { f: 'p', o: '你好，我11月20日到24日在大邱。', k: '안녕하세요, 11월 20일부터 24일까지 대구에 있어요.', t: '09:12' },
          { f: 'p', o: '想在停留期間做雷射淨膚，請問需要幾次？', k: '체류 기간에 레이저 토닝을 받고 싶은데 몇 회가 필요한가요?', t: '09:13' },
        ],
        draft: { k: '11/21(금) 오전 10시에 상담 가능합니다. 시술 횟수는 상담 후 의료진이 안내드려요. 연락받으실 메신저(LINE·WhatsApp 등)를 알려주세요.', o: '11月21日（五）上午10點可以諮詢。療程次數會在諮詢後由醫師說明。請告訴我們您方便聯絡的通訊軟體（LINE、WhatsApp等）。' } },
      { id: 'R-1044', who: '몽골 · 영어', unread: 1, title: '여드름 흉터', sub: '희망일 11/21 · 예약확인서 필요(비자)',
        sum: '몽골, 여드름 흉터 상담. 의료관광 비자용 예약확인서 요청', tags: ['여드름 흉터', '예약확인서'],
        msgs: [ { f: 'p', o: 'Hello, I need a reservation confirmation letter for my medical visa. Is 21 Nov possible?', k: '의료 비자용 예약확인서가 필요해요. 11월 21일 가능한가요?', t: '어제 18:40' } ],
        draft: { k: '11/21 오후 2시 상담 가능합니다. 예약이 확정되면 예약확인서를 영문으로 발급해 드려요.', o: 'We can see you on 21 Nov at 2 PM. Once confirmed, we will issue the reservation confirmation in English.' } },
      { id: 'R-1042', who: '일본 · 일본어', unread: 0, title: '기미 치료', sub: '시간 제안함 11/19 14:00 · 환자 답 대기',
        sum: '일본, 기미 치료. 병원이 11/19 14:00 제안, 환자 답 대기 중', tags: ['기미', '시간 제안'],
        msgs: [
          { f: 'p', o: 'シミの治療を受けたいです。18日は空いていますか？', k: '기미 치료를 받고 싶어요. 18일 비어 있나요?', t: '11/15 10:02' },
          { f: 's', k: '18일은 예약이 찼어요. 19일(수) 오후 2시는 어떠세요?', o: '18日は予約がいっぱいです。19日（水）午後2時はいかがですか？', t: '11/15 11:30' },
        ] },
    ],
    aftercare: [
      { id: 'A-219', who: '대만 · 번체', unread: 1, title: '시술 후 붉은기', sub: '방문 11/14 · 레이저 토닝 · 7시간 미답변',
        sum: '시술 3일째 붉은기가 남아 있어 정상인지 문의. 사진 1장 첨부', tags: ['붉은기', '회복·증상'],
        msgs: [
          { f: 'p', o: '做完第三天了，臉還是有點紅，這樣正常嗎？', k: '시술 3일째인데 얼굴이 아직 조금 빨개요. 정상인가요?', t: '오늘 08:05', img: true },
        ],
        draft: { k: '사진 확인했습니다. 의료진이 확인 후 오늘 안에 답변드릴게요. 그동안 세안은 미온수로 해 주세요.', o: '已收到照片。醫師確認後今天內會回覆您。在此之前請用溫水洗臉。' } },
      { id: 'A-218', who: '일본 · 일본어', unread: 0, title: '영수증 영문 재발급', sub: '방문 11/12 · 처리 중',
        sum: '귀국 전 보험 청구용 영문 영수증 재발급 요청', tags: ['영수증 재발급', '서류'],
        msgs: [
          { f: 'p', o: '保険の申請のため、英語の領収書をもう一度いただけますか？', k: '보험 청구 때문에 영문 영수증을 다시 받을 수 있을까요?', t: '11/15 21:10' },
          { f: 's', k: '네, 내일 오전까지 메일로 보내드릴게요.', o: 'はい、明日の午前中までにメールでお送りします。', t: '11/16 09:20' },
        ] },
      { id: 'A-215', who: '대만 · 번체', unread: 0, title: '재방문 예약', sub: '방문 11/08 · 완료 · 재예약 1건',
        sum: '다음 시술 가능 시기 문의 → 12/6 재예약 완료', tags: ['재방문 일정'],
        msgs: [
          { f: 'p', o: '下一次療程什麼時候可以做？', k: '다음 시술은 언제 받을 수 있나요?', t: '11/10 14:00' },
          { f: 's', k: '4주 뒤부터 가능해요. 12월 6일(토) 11시로 예약해 드릴까요?', o: '4週後から可能です。12月6日（六）11點幫您預約好嗎？', t: '11/10 15:12' },
          { f: 'p', o: '好的，謝謝！', k: '네, 감사합니다!', t: '11/10 15:20' },
        ] },
    ],
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function msgHtml(m) {
    const main = m.f === 'p' ? m.o : m.k, tr = m.f === 'p' ? '번역: ' + m.k : '환자에게 보이는 글: ' + m.o;
    // 사진·영상: 서버가 준 1시간짜리 서명된 주소 (Supabase Storage 비공개 버킷). 주소가 없으면 "사진 있음"만
    const files = (m.files || []).filter((a) => /^https:\/\//.test(a.url || ''));
    const media = files.length
      ? `<span class="media">${files.map((a) => a.kind === 'video'
        ? `<video src="${esc(a.url)}" controls preload="metadata" aria-label="${esc(a.name || '영상')}"></video>`
        // 목록에는 썸네일(결정 29), 누르면 원본. 썸네일이 없으면(예전 사진) 원본
        : `<a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer"><img src="${esc(/^https:\/\//.test(a.thumb_url || '') ? a.thumb_url : a.url)}" alt="${esc(a.name || '사진')}" loading="lazy"></a>`).join('')}</span>`
      : m.img ? '<span class="img">📷 사진 있음 (직원만 열람)</span>' : '';
    return `<div class="msg ${m.f}">${m.o === '📷' && files.length ? '' : esc(main)}${media}<span class="tr">${esc(tr)}</span><span class="t">${esc(m.t)}</span></div>`;
  }
  // HOOKS[key]가 있으면(백엔드 연결) 버튼·전송·대화 선택을 API로 처리, 없으면 예시 데이터로 화면만 바뀜
  const HOOKS = {};
  // 알림: 오른쪽 아래에 위로 쌓임. 성공은 5초 뒤 사라지고 마우스를 올리면 멈춤, 오류는 닫기(×)를 누를 때까지 남음
  const toast = (msg, bad) => {
    let box = document.getElementById('toasts');
    if (!box) { box = document.createElement('div'); box.id = 'toasts'; box.setAttribute('aria-live', 'polite'); host.append(box); }
    const el = document.createElement('div');
    el.className = 'toast' + (bad ? ' bad' : '');
    el.setAttribute('role', bad ? 'alert' : 'status');
    const text = document.createElement('span'); text.textContent = msg;
    const x = document.createElement('button'); x.type = 'button'; x.className = 'toast-x'; x.setAttribute('aria-label', '알림 닫기'); x.textContent = '×';
    x.onclick = () => el.remove();
    el.append(text, x); box.append(el);
    if (bad) return; // 오류는 직접 닫을 때까지
    let timer = setTimeout(() => el.remove(), 5000);
    el.onmouseenter = () => clearTimeout(timer);
    el.onmouseleave = () => { timer = setTimeout(() => el.remove(), 2000); };
  };
  function renderChat(root, key, idx) {
    const list = CHATS[key];
    if (!list.length) {
      root.querySelector('.clist').innerHTML = '<p class="note" style="padding:14px">대화가 없어요</p>';
      ['.chead', '.csum', '.cmsgs', '.cdraft'].forEach((s) => root.querySelector(s).innerHTML = '');
      return;
    }
    idx = Math.min(idx, list.length - 1);
    const c = list[idx], hook = HOOKS[key];
    root.dataset.idx = idx;
    root.querySelector('.clist').innerHTML = list.map((x, i) =>
      `<button class="citem${i === idx ? ' on' : ''}" data-i="${i}"><b>${esc(x.id)} · ${esc(x.who)}${x.unread ? `<span class="dot">${x.unread}</span>` : ''}</b><small>${esc(x.title)}</small><small>${esc(x.sub)}</small></button>`).join('');
    const acts = key === 'booking' ? headActs(chatReq(c))
      : '<button class="btn" data-head="in_progress">처리 중</button><button class="btn primary" data-head="resolved">해결됨</button>';
    root.querySelector('.chead').innerHTML = `<div><b>${esc(c.id)} · ${esc(c.title)}</b><br><small>${esc(c.who)} · ${esc(c.sub)}</small></div><div style="display:flex;gap:6px">${acts}</div>`;
    root.querySelector('.csum').innerHTML = `<b>${hook ? '요약' : 'AI 요약'}</b> ${esc(c.sum)}<div class="chips">${c.tags.map((t) => `<span class="chip">${esc(t)}</span>`).join('')}</div>`;
    const box = root.querySelector('.cmsgs'); box.innerHTML = c.msgs.map(msgHtml).join(''); box.scrollTop = box.scrollHeight;
    root.querySelector('.cdraft').innerHTML = c.draft
      ? `<b>AI 답장 초안</b> (직원 승인 후 발송)<br>${esc(c.draft.k)}<div class="note" style="margin:4px 0 0">환자에게: ${esc(c.draft.o)}</div><div class="acts"><button class="btn primary" data-act="send">승인·발송</button><button class="btn" data-act="edit">고쳐서 보내기</button></div>` : '';
    root.querySelectorAll('.citem').forEach((b) => b.onclick = async () => {
      const i = +b.dataset.i;
      markSeen(key, list[i]); // 이 항목을 열어 봄 → 메뉴 숫자에서 빠짐
      if (hook && hook.select) await hook.select(list[i]);
      renderChat(root, key, i);
    });
    root.querySelectorAll('[data-head]').forEach((b) => b.onclick = async () => {
      const act = b.dataset.head;
      if (key === 'booking') {
        const r = chatReq(c);
        const done = act === 'view' ? await viewProposal(r) : await bookingAct(r, act);
        if (done && !API.ready) renderChat(root, key, idx);
        return;
      }
      await aftercareAct(c, act, root, idx);
    });
    // 환자에게 보내는 글은 모두 확인 창을 거친다 (AI 초안은 직원 승인 후 발송, compliance)
    const deliver = async (k, o) => {
      if (hook) { await hook.send(c, k, root); return; }
      c.msgs.push({ f: 's', k, o, t: '방금' }); c.draft = null; c.unread = 0; renderChat(root, key, idx); updateNav();
      toast('보냈어요 (예시 — 저장 안 됨)');
    };
    const note = '환자 언어 번역은 연결 전이라 한국어 원문으로 저장돼요.';
    const send = async (k, o, title) => {
      const ok = await dialog({ title: title || '환자에게 보낼까요?', ok: '보내기',
        body: `<div class="dlg-sum"><b>보낼 내용</b><p>${esc(k)}</p>${o && !o.startsWith('(') ? `<small>환자에게 보이는 글: ${esc(o)}</small>` : ''}</div><p class="note">${note}</p>` });
      if (!ok) return false;
      await deliver(k, o); return true;
    };
    const d = root.querySelector('[data-act=send]'); if (d) d.onclick = () => send(c.draft.k, c.draft.o, 'AI 초안을 승인하고 보낼까요?');
    const e = root.querySelector('[data-act=edit]'); if (e) e.onclick = async () => {
      const k = await dialog({ title: '고쳐서 보내기', ok: '보내기', body: field('보낼 내용 (한국어)', `<textarea name="k" rows="4">${esc(c.draft.k)}</textarea>`) + `<p class="note">${note}</p>`,
        onOk: (f) => f.k.value.trim() || fail('내용을 입력해 주세요') });
      if (k) await deliver(k, '(AI 번역되어 전송됨)');
    };
    root.querySelector('.cinput').onsubmit = async (ev) => {
      ev.preventDefault();
      const inp = root.querySelector('.cinput input'), v = inp.value.trim();
      if (v && await send(v, '(AI 번역되어 전송됨)')) inp.value = '';
    };
  }

  // ---------- 직원 로그인 · 백엔드 연결 (GET /api/v1/tenant/analytics/summary) ----------
  // 직원 토큰은 환자 사이트와 같은 곳(이 탭 sessionStorage, features/staff/staffSession.ts)에 둔다.
  // 환자 사이트 "병원 관계자 로그인" 또는 이 화면의 "직원 로그인"으로 받음. 만료(401)되면 지우고 로그인 화면으로
  const apiBase = () => API_BASE;
  function setLoggedIn(on) {
    document.getElementById('loginBtn').hidden = on;
    document.getElementById('logoutBtn').hidden = !on;
  }
  function expired() {
    clearStaffToken();
    setLoggedIn(false);
    toast('로그인이 만료됐어요. 다시 로그인해 주세요', true);
    timers.push(setTimeout(() => onLeave(), 1500)); // 로그인 화면으로 (DB 값이 남지 않게)
  }
  document.getElementById('loginBtn').onclick = async () => {
    const token = await dialog({
      title: '직원 로그인', ok: '로그인',
      body: field('이메일', '<input name="email" type="email" autocomplete="username" required>')
        + field('비밀번호', '<input name="pw" type="password" autocomplete="current-password" required>')
        + '<p class="note">입점 병원 직원 계정. 가입은 환자 사이트의 "병원 관계자"에서 해요.</p>',
      onOk: async (f) => {
        const email = f.email.value.trim(), password = f.pw.value;
        if (!email || !password) fail('이메일과 비밀번호를 입력해 주세요');
        let res;
        try {
          res = await fetch(apiBase() + '/auth/staff/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
        } catch (e) { fail('서버에 연결하지 못했어요 (' + apiBase() + ')'); }
        const body = await res.json().catch(() => ({}));
        if (res.status === 401 || body.code === 'auth.invalid_credentials') fail('이메일 또는 비밀번호가 맞지 않아요');
        if (body.code === 'auth.too_many_attempts') fail('여러 번 틀려서 잠시 막혔어요. 조금 뒤 다시 해 주세요');
        if (!res.ok) fail('로그인하지 못했어요: ' + (body.code || res.status));
        return body.access_token;
      },
    });
    if (!token) return;
    saveStaffToken(token);
    toast('로그인했어요');
    connectApi();
  };

  async function connectApi() {
    const token = readStaffToken(), api = apiBase();
    const src = document.getElementById('dataSrc');
    if (!token) { src.textContent = '예시 데이터'; return; }
    try {
      setLoggedIn(true);
      const res = await fetch(api + '/tenant/analytics/summary', { headers: { Authorization: 'Bearer ' + token } });
      if (res.status === 401) return expired();
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).code || res.status);
      const s = await res.json();
      const fmt = (n) => (n == null ? '집계 전' : n.toLocaleString('ko-KR'));
      for (const k of s.kpi) {
        const v = document.getElementById('k_' + k.key), d = document.getElementById('d_' + k.key), f = document.getElementById('f_' + k.key);
        const text = k.now == null ? '집계 전' : k.unit === 'percent' ? k.now + '%' : fmt(k.now);
        if (v) v.textContent = text;
        if (f) f.textContent = k.now == null ? '—' : fmt(k.now);
        if (d) {
          if (k.now == null || k.prev == null) { d.textContent = k.now == null ? '방문 기록 테이블 연결 전' : '비교 기간 데이터 없음'; d.className = 'note'; }
          else {
            const diff = k.unit === 'percent' ? k.now - k.prev : k.prev ? Math.round((k.now - k.prev) / k.prev * 100) : 0;
            const good = k.lowerIsBetter ? diff <= 0 : diff >= 0;
            d.textContent = (diff >= 0 ? '▲ ' : '▼ ') + Math.abs(diff) + (k.unit === 'percent' ? '%p' : '%'); d.className = good ? 'up' : 'down';
          }
        }
      }
      document.getElementById('tNew').textContent = s.today.newRequests;
      document.getElementById('tVisit').textContent = s.today.visitsToday;
      document.getElementById('tVisitG').textContent = '확정된 오늘 예약 →';
      document.getElementById('todoTotal').textContent = (s.today.newRequests + s.today.visitsToday) + '건 (예약 기준)';
      src.textContent = 'DB 연결됨 · ' + s.period.from + '~' + s.period.to; src.className = 'badge';
      if (!API.ready) { API.base = api; API.token = token; API.ready = true; await setupApi(); }
    } catch (e) {
      src.textContent = 'DB 연결 실패 (' + e.message + ') · 예시 데이터'; src.className = 'badge bad';
    }
  }

  // ---------- 상담 확정·사후관리를 백엔드에 연결 ----------
  const API = { base: '', token: '', ready: false };
  async function call(path, opts = {}) {
    const res = await fetch(API.base + path, {
      ...opts,
      headers: { Authorization: 'Bearer ' + API.token, ...(opts.body ? { 'Content-Type': 'application/json' } : {}) },
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) { expired(); throw new Error('auth.required'); }
    if (!res.ok) throw new Error(body.code || res.status);
    return body;
  }
  const NAT = { TW: '대만', CN: '중국', JP: '일본', MN: '몽골', VN: '베트남', US: '미국', TH: '태국' };
  const LANG = { 'zh-TW': '번체', 'zh-CN': '간체', en: '영어', vi: '베트남어', ko: '한국어' };
  const TRT = { laser_toning: '레이저 토닝', acne_scar: '여드름 흉터', botox: '보톡스', melasma: '기미 치료', filler: '필러' };
  const AC_STATUS = { new: '새 문의', in_progress: '처리 중', resolved: '해결됨' };
  const kdate = (iso) => iso ? new Date(iso).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit' }) : '—';
  const short = (id) => String(id).slice(0, 4).toUpperCase();
  const chatRoot = (key) => document.querySelector(`.chat[data-chat=${key}]`);

  async function loadBooking(keepId) {
    // 확정된 예약도: 방문 전 환자 질문(결정 32)이 확정 뒤에도 올 수 있음
    const [p, q, c] = await Promise.all(['pending', 'proposed', 'confirmed'].map((st) => call(`/tenant/booking-requests?status=${st}`)));
    // 마지막 글이 환자 질문이면 아직 답 안 함 → 빨간 숫자
    const lastAsk = (r) => Math.max(0, ...(r.questions || []).map((x) => Date.parse(x.created_at)));
    const lastReply = (r) => Math.max(0, ...(r.replies || []).map((x) => Date.parse(x.sent_at)));
    CHATS.booking = [...p, ...q, ...c].map((r) => ({
      req: toR(r), rid: r.id, id: 'R-' + short(r.id), who: `${NAT[r.nationality] || r.nationality} · ${LANG[r.lang] || r.lang}`,
      // 빨간 숫자: 대기 중인데 병원 답장이 아직 없으면 1 (답장은 서버에 저장 → 새로고침해도 유지)
      unread: (r.status === 'pending' && !(r.replies || []).length) || lastAsk(r) > lastReply(r) ? 1 : 0, title: TRT[r.treatment] || r.treatment || '상담',
      sub: (r.status === 'proposed' ? '시간 제안함 ' + kdate(r.confirmed_slot) : r.status === 'confirmed' ? '확정 ' + kdate(r.confirmed_slot) : '희망 ' + kdate(r.preferred_slots[0])) + (r.visa_needed ? ' · 예약확인서 필요' : ''),
      slots: r.preferred_slots, sum: r.message_translated || '(번역 전)',
      tags: [TRT[r.treatment] || r.treatment, '희망일 ' + r.preferred_slots.length + '개', r.visa_needed ? '비자 서류' : '비자 불필요'].filter(Boolean),
      msgs: [
        ...(r.message_original ? [{ f: 'p', o: r.message_original, k: r.message_translated || '(번역 전)', t: kdate(r.created_at) }] : []),
        // 답장과 방문 전 환자 질문(결정 32)을 시간 순으로
        ...[
          ...(r.replies || []).map((x) => ({ at: x.sent_at, m: { f: 's', k: x.text_ko, o: x.text_translated || '(번역 연결 전 — 환자에게 한국어 원문)', t: kdate(x.sent_at) } })),
          ...(r.questions || []).map((x) => ({ at: x.created_at, m: { f: 'p', o: x.text_original, k: x.text_translated || '(번역 전 — 번역 동의 없음)', t: kdate(x.created_at) } })),
        ].sort((a, b) => Date.parse(a.at) - Date.parse(b.at)).map((x) => x.m),
      ],
    }));
    const i = Math.max(0, CHATS.booking.findIndex((c) => c.rid === keepId));
    renderChat(chatRoot('booking'), 'booking', i);
  }

  async function openThread(c) {
    const th = await call('/tenant/aftercare/' + c.tid);
    c.msgs = th.messages.map((m) => m.sender === 'patient'
      ? { f: 'p', o: m.text_original, k: m.text_translated || '(번역 전)', t: kdate(m.created_at), img: m.has_photo, files: m.attachments || [] }
      : { f: 's', k: m.text_original, o: m.text_translated || '(번역 연결 전)', t: kdate(m.created_at) });
    c.sub = AC_STATUS[th.status] + ' · 방문 ' + kdate(th.visited_slot);
    c.loaded = true;
  }
  async function loadAftercare(keepId) {
    const list = await call('/tenant/aftercare');
    CHATS.aftercare = list.map((th) => ({
      tid: th.id, id: 'A-' + short(th.id), who: `${NAT[th.nationality] || th.nationality} · ${LANG[th.lang] || th.lang}`,
      status: th.status, unread: th.status === 'resolved' ? 0 : th.unanswered, title: (th.tags[0] || TRT[th.treatment] || '사후관리'), sub: AC_STATUS[th.status] + ' · 방문 ' + kdate(th.visited_slot),
      sum: th.last_message || '', tags: th.tags.length ? th.tags : [TRT[th.treatment] || '태그 없음'], msgs: [],
    }));
    let i = Math.max(0, CHATS.aftercare.findIndex((c) => c.tid === keepId));
    if (CHATS.aftercare[i]) await openThread(CHATS.aftercare[i]);
    renderChat(chatRoot('aftercare'), 'aftercare', i);
    updateNav();
  }

  // ---------- 열람 기록 (GET /tenant/audit-logs) ----------
  const AUDIT = { 'booking.list': '요청 목록 열람', 'booking.view': '요청서 열람', 'booking.reply': '상담 답장',
    'aftercare.view': '사후관리 대화 열람', 'aftercare.reply': '사후관리 답장' };
  async function loadAudit() {
    const rows = await call('/tenant/audit-logs?limit=50');
    const staffNo = {};
    const who = (a) => (staffNo[a] ??= '직원 ' + (Object.keys(staffNo).length + 1)); // 직원 id는 화면에 그대로 안 보임
    const ref = (r) => { const [k, id] = r.split(':'); return k === 'booking_requests' ? id + '건' : k === 'aftercare_thread' ? 'A-' + short(id) : 'R-' + short(id); };
    document.getElementById('auditRows').innerHTML = rows.length
      ? rows.map((x) => `<tr><td>${esc(kdate(x.created_at))}</td><td>${esc(who(x.actor))}</td><td>${esc(AUDIT[x.action] || x.action)}</td><td>${esc(ref(x.ref))}</td></tr>`).join('')
      : '<tr><td colspan="4" class="note">아직 기록이 없어요</td></tr>';
    const src = document.getElementById('auditSrc'); src.textContent = 'DB · 최근 ' + rows.length + '줄'; src.className = 'badge';
  }
  document.getElementById('auditReload').onclick = async () => {
    if (!API.ready) return toast('직원 로그인 뒤에 실제 기록을 볼 수 있어요');
    try { await loadAudit(); toast('열람 기록을 새로 불러왔어요'); } catch (e) { toast(why(e), true); }
  };

  async function setupApi() {
    try {
      loadAudit().catch(() => {});
      const me = await call('/tenant/me');
      document.querySelector('.hosp b').textContent = me.display_name;
      state.ac = me.aftercare_enabled;
      document.querySelectorAll('#acSwitch button').forEach((b) => b.classList.toggle('on', (b.dataset.v === 'on') === state.ac));
      render();
      HOOKS.booking = {
        async send(c, text) {
          try { await call(`/tenant/booking-requests/${c.rid}/replies`, { method: 'POST', body: JSON.stringify({ text }) }); toast('답장을 보냈어요 (DB 저장)'); }
          catch (e) { toast('전송 실패: ' + e.message, true); return; }
          await loadBooking(c.rid); updateNav(); // 서버에서 다시 불러와 답장·빨간 숫자 반영
        },
      };
      HOOKS.aftercare = {
        select: openThread,
        async send(c, text) {
          try { await call(`/tenant/aftercare/${c.tid}/messages`, { method: 'POST', body: JSON.stringify({ text }) }); toast('답장을 보냈어요 (DB 저장)'); }
          catch (e) { toast('전송 실패: ' + e.message, true); }
          await loadAftercare(c.tid);
        },
      };
      await Promise.all([loadBooking(), loadAftercare(), loadRequests()]);
    } catch (e) {
      toast('API 연결 실패: ' + e.message, true);
    }
  }


  // ---------- 다이얼로그 (모든 버튼 공통) ----------
  // 저장·상태 변경 버튼은 모두 확인 창을 거친다. 서버 API가 아직 없는 기능은 창까지 만들고 "화면에만 반영"으로 안내
  const SCREEN_ONLY = '화면에만 반영됐어요 (서버 연결 전 기능이라 저장되지 않아요)';
  const ERR = {
    'booking.invalid_transition': '이미 다른 상태로 바뀐 요청이에요. 목록을 새로 불러왔어요',
    validation: '입력값을 확인해 주세요', not_found: '요청을 찾을 수 없어요 (다른 곳에서 바뀌었을 수 있어요)',
    'auth.required': '로그인이 만료됐어요. 다시 로그인해 주세요', 'auth.forbidden': '이 계정으로는 할 수 없어요',
  };
  const why = (e) => ERR[e.message] || ('저장하지 못했어요: ' + e.message);
  function dialog({ title, body = '', ok = '확인', cancel = '취소', danger = false, onOk, extra, extras }) {
    return new Promise((resolve) => {
      const wrap = document.createElement('div');
      wrap.className = 'dlg-wrap';
      wrap.innerHTML = `<form class="dlg" role="dialog" aria-modal="true" aria-labelledby="dlgTitle" novalidate>
        <h3 id="dlgTitle">${esc(title)}</h3><div class="dlg-body">${body}</div><p class="dlg-err" role="alert" hidden></p>
        <div class="dlg-acts">${(extras || (extra ? [extra] : [])).map((x, i) => `<button type="button" class="btn${x.danger ? ' danger' : x.primary ? ' primary' : ''}" data-x="extra" data-i="${i}">${esc(x.label)}</button>`).join('')}<span style="flex:1"></span>
        ${cancel ? `<button type="button" class="btn" data-x="cancel">${esc(cancel)}</button>` : ''}
        <button type="submit" class="btn ${danger ? 'danger' : 'primary'}">${esc(ok)}</button></div></form>`;
      const form = wrap.querySelector('form'), err = wrap.querySelector('.dlg-err'), back = document.activeElement;
      const close = (v) => { wrap.remove(); document.removeEventListener('keydown', onKey); if (back && back.focus) back.focus(); resolve(v); };
      const onKey = (e) => { if (e.key === 'Escape') close(null); };
      document.addEventListener('keydown', onKey);
      cleanups.push(() => document.removeEventListener('keydown', onKey));
      wrap.addEventListener('mousedown', (e) => { if (e.target === wrap) close(null); });
      wrap.querySelector('[data-x=cancel]')?.addEventListener('click', () => close(null));
      wrap.querySelectorAll('[data-x=extra]').forEach((b) => b.addEventListener('click', () => { close(null); (extras || [extra])[+b.dataset.i].onClick(); }));
      form.onsubmit = async (e) => {
        e.preventDefault();
        const sub = form.querySelector('[type=submit]');
        err.hidden = true; sub.disabled = true;
        try { const v = onOk ? await onOk(form) : true; close(v === undefined ? true : v); }
        catch (x) { err.textContent = x.message; err.hidden = false; sub.disabled = false; }
      };
      host.append(wrap);
      (form.querySelector('.dlg-body input:not([type=radio]), .dlg-body select, .dlg-body textarea, .dlg-body input:checked') || form.querySelector('[type=submit]')).focus();
    });
  }
  const fail = (msg) => { throw new Error(msg); };
  const field = (label, html) => `<label class="f">${esc(label)}${html}</label>`;
  const won2 = (n) => '₩' + Number(n).toLocaleString('ko-KR');

  // ---------- 상담·예약: 확정 · 시간 제안 · 거절 · 방문 완료 · 미방문 ----------
  const REJECT = { fully_booked: '예약이 마감됐어요', not_offered: '하지 않는 진료예요', needs_consult: '대면 상담이 먼저 필요해요', other: '기타' };
  const ST = { pending: ['대기', 'gray'], proposed: ['시간 제안함', 'warn'], confirmed: ['확정', ''], visited: ['방문 완료', ''],
    no_show: ['미방문', 'bad'], rejected: ['거절', 'gray'], cancelled: ['환자 취소', 'gray'], expired: ['기간 지남', 'gray'] };
  const NEXT = { confirm: 'confirmed', propose: 'proposed', reject: 'rejected', visited: 'visited', no_show: 'no_show' };
  const DONE = { confirm: '예약을 확정했어요', propose: '다른 시간을 제안했어요', reject: '요청을 거절했어요', visited: '방문 완료로 바꿨어요', no_show: '미방문으로 바꿨어요' };
  const kst = (d, t) => new Date(`${d}T${t}:00+09:00`).toISOString();
  const todayKst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
  const plusDays = (n) => new Date(Date.now() + (9 + 24 * n) * 3600e3).toISOString().slice(0, 10);
  // 예시 데이터 (토큰 없이 열었을 때)
  let REQS = [
    { rid: null, id: 'R-1043', who: '대만 · 번체', title: '레이저 토닝', status: 'pending', visa: false, slots: [kst(plusDays(3), '10:00'), kst(plusDays(4), '14:00')], msg_k: '레이저 토닝 몇 회가 필요한가요?' },
    { rid: null, id: 'R-1044', who: '몽골 · 영어', title: '여드름 흉터', status: 'pending', visa: true, slots: [kst(plusDays(3), '11:00')], msg_k: '의료 비자용 예약확인서가 필요해요' },
    { rid: null, id: 'R-1042', who: '일본 · 일본어', title: '기미 치료', status: 'proposed', visa: false, slots: [kst(plusDays(1), '10:00')], confirmed_slot: kst(plusDays(1), '14:00'), msg_k: '기미 치료 예약하고 싶어요' },
    { rid: null, id: 'R-1040', who: '중국 · 간체', title: '보톡스', status: 'confirmed', visa: false, slots: [kst(todayKst(), '10:00')], confirmed_slot: kst(todayKst(), '10:00') },
    { rid: null, id: 'R-1041', who: '대만 · 번체', title: '여드름 흉터', status: 'confirmed', visa: false, slots: [kst(plusDays(2), '10:30')], confirmed_slot: kst(plusDays(2), '10:30') },
  ];
  function toR(r) {
    return { rid: r.id, id: 'R-' + short(r.id), who: `${NAT[r.nationality] || r.nationality} · ${LANG[r.lang] || r.lang}`,
      title: TRT[r.treatment] || r.treatment || '상담', status: r.status, visa: r.visa_needed, slots: r.preferred_slots,
      confirmed_slot: r.confirmed_slot, msg_o: r.message_original, msg_k: r.message_translated };
  }
  function chatReq(c) {
    const ex = !c.req && REQS.find((x) => !x.rid && x.id === c.id);
    if (ex) { ex.demoChat = c; return ex; }
    return c.req || { rid: null, id: c.id, who: c.who, title: c.title, status: 'pending', visa: /예약확인서/.test(c.sub),
      slots: [kst(plusDays(3), '10:00'), kst(plusDays(4), '14:00')], msg_k: c.sum, demoChat: c };
  }
  function reqSummary(r) {
    return `<div class="dlg-sum"><b>${esc(r.id)} · ${esc(r.title)}</b><small>${esc(r.who)}${r.visa ? ' · 예약확인서 필요' : ''}</small>${r.msg_k ? `<p>“${esc(r.msg_k)}”</p>` : ''}</div>`;
  }
  function slotOptions(opts, custom) {
    const times = [];
    for (let h = 9; h < 19; h++) for (const m of ['00', '30']) times.push(`${String(h).padStart(2, '0')}:${m}`);
    return `<div class="opts">${opts.map((o, i) => `<label class="opt"><input type="radio" name="slot" value="${esc(o.iso)}"${i === 0 ? ' checked' : ''}><span><b>${esc(kdate(o.iso))}</b> <small>${esc(o.label)}</small></span></label>`).join('')}
      ${custom ? `<label class="opt"><input type="radio" name="slot" value="custom"${opts.length ? '' : ' checked'}><span><b>다른 시간 직접 입력</b></span></label>
      <div class="pick"><input type="date" name="d" min="${todayKst()}" value="${plusDays(1)}" aria-label="날짜"><select name="t" aria-label="시간">${times.map((t) => `<option${t === '10:00' ? ' selected' : ''}>${t}</option>`).join('')}</select><small>한국 시간 · 30분 단위</small></div>` : ''}</div>`;
  }
  function pickedSlot(f) {
    const v = f.querySelector('input[name=slot]:checked')?.value || fail('시간을 골라 주세요');
    const iso = v === 'custom' ? kst(f.d.value || fail('날짜를 골라 주세요'), f.t.value) : v;
    if (new Date(iso) <= new Date()) fail('지난 시간은 고를 수 없어요');
    return iso;
  }
  async function bookingAct(r, act) {
    const S = reqSummary(r);
    const cfg = {
      confirm: () => {
        const opts = r.status === 'proposed' && r.confirmed_slot ? [{ iso: r.confirmed_slot, label: '병원이 제안한 시간' }]
          : r.slots.map((iso, i) => ({ iso, label: `환자 희망 ${i + 1}` }));
        return { title: '예약을 확정할까요?', ok: '예약 확정', body: S + '<b>확정할 시간</b>' + slotOptions(opts, false)
          + '<p class="note">확정하면 환자 화면에 “확정”으로 보이고 캘린더·오늘 할 일에 들어가요.</p>', slot: true };
      },
      propose: () => ({ title: '다른 시간을 제안할까요?', ok: '시간 제안 보내기',
        body: S + '<b>제안할 시간</b>' + slotOptions(r.slots.map((iso, i) => ({ iso, label: `환자 희망 ${i + 1}` })), true)
          + '<p class="note">환자가 수락하면 확정돼요. 수락 전에는 다른 시간으로 다시 제안할 수 있어요.</p>', slot: true }),
      reject: () => ({ title: '이 요청을 거절할까요?', ok: '거절', danger: true,
        body: S + field('거절 사유', `<select name="reason" required><option value="">사유를 골라 주세요</option>${Object.entries(REJECT).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select>`)
          + '<p class="note">거절하면 되돌릴 수 없어요. 사유는 상태 기록에 남아요.</p>', reason: true }),
      visited: () => ({ title: '방문 완료로 바꿀까요?', ok: '방문 완료',
        body: S + `<p>확정 시간: <b>${esc(kdate(r.confirmed_slot))}</b></p><p class="note">방문 완료 건은 “진료·결제 확인”에서 결제 금액을 입력해요 (수수료 기준). 사후관리 대화도 이때부터 열려요.</p>` }),
      no_show: () => ({ title: '미방문으로 바꿀까요?', ok: '미방문', danger: true,
        body: S + `<p>확정 시간: <b>${esc(kdate(r.confirmed_slot))}</b></p><p class="note">되돌릴 수 없어요. 미방문은 수수료가 생기지 않아요.</p>` }),
    }[act]();
    const out = await dialog({ ...cfg, onOk: async (f) => {
      const body = {};
      if (cfg.slot) body.slot = pickedSlot(f);
      if (cfg.reason) body.reason = f.reason.value || fail('거절 사유를 골라 주세요');
      if (!API.ready) return { demo: true, slot: body.slot };
      try { return await call(`/tenant/booking-requests/${r.rid}/${act === 'no_show' ? 'no-show' : act}`, { method: 'POST', body: JSON.stringify(body) }); }
      catch (e) { if (e.message === 'booking.invalid_transition' || e.message === 'not_found') refreshBooking(r.rid); fail(why(e)); }
    } });
    if (!out) return false;
    if (out.demo) {
      r.status = NEXT[act];
      if (out.slot) r.confirmed_slot = out.slot;
      if (r.demoChat) { r.demoChat.sub = `${ST[r.status][0]} (예시)`; r.demoChat.unread = 0; }
      const broot = chatRoot('booking'); renderChat(broot, 'booking', +broot.dataset.idx || 0);
      toast(DONE[act] + ' (예시 — 저장 안 됨)'); renderReqs(); updateNav(); return true;
    }
    toast(DONE[act] + (out.confirmed_slot && act !== 'reject' ? ': ' + kdate(out.confirmed_slot) : '') + ' (DB 저장)');
    await refreshBooking(r.rid);
    return true;
  }
  function viewProposal(r) {
    return dialog({ title: '제안한 시간', ok: '닫기', cancel: '', extra: { label: '다른 시간 다시 제안', onClick: () => bookingAct(r, 'propose') },
      body: reqSummary(r) + `<div class="row"><span>제안한 시간</span><b>${esc(kdate(r.confirmed_slot))}</b></div>
        <div class="row"><span>환자 희망</span><span>${r.slots.map((s) => esc(kdate(s))).join('<br>')}</span></div>
        <div class="row"><span>환자 응답</span><span class="badge warn">수락 대기 중</span></div>
        <p class="note">환자가 수락하면 자동으로 확정돼요. 상담 답장 기록은 답장 API가 생기면 여기에 함께 보여요.</p>` });
  }
  function rowActs(r) {
    return r.status === 'pending' ? '<button class="btn primary" data-a="confirm">확정</button> <button class="btn" data-a="propose">시간 제안</button> <button class="btn" data-a="reject">거절</button>'
      : r.status === 'proposed' ? '<button class="btn" data-a="view">제안 보기</button> <button class="btn" data-a="reject">거절</button>'
      : r.status === 'confirmed' ? '<button class="btn primary" data-a="visited">방문 완료</button> <button class="btn" data-a="no_show">미방문</button>' : '';
  }
  const headActs = (r) => r.status === 'pending'
    ? '<button class="btn primary" data-head="confirm">예약 확정</button><button class="btn" data-head="propose">시간 제안</button><button class="btn" data-head="reject">거절</button>'
    : r.status === 'proposed' ? '<button class="btn" data-head="view">제안 보기</button><button class="btn" data-head="reject">거절</button>' : '';
  function renderReqs() {
    const tb = document.getElementById('reqRows');
    tb.innerHTML = REQS.length ? REQS.map((r, i) => `<tr data-i="${i}"><td>${esc(r.id)}</td><td>${esc(r.who)}</td><td>${esc(r.title)}</td>
      <td>${r.confirmed_slot && r.status !== 'pending' ? esc(kdate(r.confirmed_slot)) : esc(kdate(r.slots[0]))}${r.status === 'pending' && r.slots.length > 1 ? ` <small>외 ${r.slots.length - 1}개</small>` : ''}</td>
      <td>${r.visa ? '<span class="badge warn">예약확인서 필요</span>' : '불필요'}</td><td><span class="badge ${ST[r.status][1]}">${ST[r.status][0]}</span></td><td style="white-space:nowrap">${rowActs(r)}</td></tr>`).join('')
      : '<tr><td colspan="7" class="note">처리할 요청이 없어요</td></tr>';
    renderCal();
    tb.querySelectorAll('[data-a]').forEach((b) => b.onclick = () => {
      const r = REQS[+b.closest('tr').dataset.i];
      return b.dataset.a === 'view' ? viewProposal(r) : bookingAct(r, b.dataset.a);
    });
  }
  async function loadRequests() {
    const [p, q, c, v, n] = await Promise.all(['pending', 'proposed', 'confirmed', 'visited', 'no_show'].map((s) => call('/tenant/booking-requests?status=' + s)));
    REQS = [...p, ...q, ...c.sort((a, b) => String(a.confirmed_slot).localeCompare(String(b.confirmed_slot)))].map(toR);
    DONE_REQS = [...v, ...n].map(toR);
    const src = document.getElementById('reqSrc'); src.textContent = 'DB · 대기 ' + p.length + ' · 제안 ' + q.length + ' · 확정 ' + c.length; src.className = 'badge';
    renderReqs(); updateNav();
  }
  async function refreshBooking(keep) {
    if (!API.ready) return;
    await Promise.all([loadBooking(keep), loadRequests(), connectApi()]).catch((e) => toast(why(e), true));
  }

  // ---------- 사후관리: 처리 중 · 해결됨 · 지원 스위치 ----------
  async function aftercareAct(c, act, root, idx) {
    const tags = (c.tags || []).filter((t) => t !== '태그 없음').join(', ');
    const out = await dialog({
      title: act === 'resolved' ? '해결됨으로 바꿀까요?' : '처리 중으로 바꿀까요?', ok: act === 'resolved' ? '해결됨' : '처리 중',
      body: `<div class="dlg-sum"><b>${esc(c.id)} · ${esc(c.title)}</b><small>${esc(c.who)} · ${esc(c.sub)}</small></div>`
        + (act === 'resolved' ? field('태그 (쉼표로 구분, 통계·비슷한 문의 찾기에 쓰여요)', `<input type="text" name="tags" value="${esc(tags)}">`)
          + '<p class="note">해결된 대화도 환자가 다시 글을 쓰면 새 문의로 열려요.</p>' : '<p class="note">다른 직원에게 “누가 보고 있음”으로 보여요.</p>'),
      onOk: async (f) => {
        const body = { status: act };
        if (f.tags) body.tags = f.tags.value.split(',').map((t) => t.trim()).filter(Boolean);
        if (!API.ready) return { demo: true, body };
        try { await call('/tenant/aftercare/' + c.tid, { method: 'PATCH', body: JSON.stringify(body) }); }
        catch (e) { fail(why(e)); }
      },
    });
    if (!out) return;
    if (out.demo) { c.sub = AC_STATUS[act] + ' (예시)'; if (out.body.tags) c.tags = out.body.tags; if (act === 'resolved') c.unread = 0; updateNav(); toast(AC_STATUS[act] + '(으)로 바꿨어요 (예시 — 저장 안 됨)'); renderChat(root, 'aftercare', idx); return; }
    toast(AC_STATUS[act] + '(으)로 바꿨어요 (DB 저장)'); await loadAftercare(c.tid);
  }
  async function acToggle(on) {
    if (on === state.ac) return;
    const out = await dialog({
      title: on ? '사후관리 지원을 켤까요?' : '사후관리 지원을 끌까요?', ok: on ? '켜기' : '끄기', danger: !on,
      body: on ? '<p>환자 사이트 “사후관리 지원” 필터에 이 병원이 나오고, 방문 완료 환자가 사후관리 대화를 열 수 있어요.</p><p class="note">사후관리는 기본·프리미엄 모두 쓸 수 있어요 (요금 v4).</p>'
        : '<p>“사후관리 지원” 필터에서 빠지고, 환자가 <b>새</b> 사후관리 대화를 열 수 없어요. 이미 열린 대화는 그대로 볼 수 있어요.</p><p class="note">회원 등급·요금은 바뀌지 않아요.</p>',
      onOk: async () => {
        if (!API.ready) return { demo: true };
        try { return await call('/tenant/me', { method: 'PATCH', body: JSON.stringify({ aftercare_enabled: on }) }); } catch (e) { fail(why(e)); }
      },
    });
    if (!out) return;
    state.ac = out.demo ? on : out.aftercare_enabled;
    document.querySelectorAll('#acSwitch button').forEach((x) => x.classList.toggle('on', (x.dataset.v === 'on') === state.ac));
    render(); toast((state.ac ? '사후관리 지원을 켰어요' : '사후관리 지원을 껐어요') + (out.demo ? ' (예시 — 저장 안 됨)' : ' (DB 저장)'));
  }
  document.querySelectorAll('#acSwitch button').forEach((b) => b.onclick = () => acToggle(b.dataset.v === 'on'));

  // ---------- 서버 API가 아직 없는 버튼: 창까지 만들고 화면에만 반영 ----------
  const markDone = (b) => { const o = b.closest('.check')?.querySelector('.o'); if (o) o.classList.add('done'); };
  const setRow = (label, html) => document.querySelectorAll('#settings .row').forEach((r) => { if (r.firstElementChild?.textContent === label) r.lastElementChild.innerHTML = html; });
  const DLG = {
    async receipt(b) {
      const tr = b.closest('tr'), id = tr.cells[0].textContent;
      const out = await dialog({ title: id + ' 결제 금액·영수증', ok: '저장',
        body: field('결제 금액 (원, 부가세 제외)', '<input type="number" name="amt" min="1" step="1" required inputmode="numeric">')
          + field('결제 수단', '<select name="pay"><option>카드</option><option>현금</option><option>계좌이체</option></select>')
          + field('영수증 (사진·PDF)', '<input type="file" name="file" accept="image/*,application/pdf">')
          + '<p class="note">환자가 금액을 확인하면 “확인 완료”가 되고, 수수료(기본 13% · 프리미엄 8%)는 확인된 금액 기준이에요.</p>',
        onOk: (f) => { const a = +f.amt.value; if (!(a > 0)) fail('결제 금액을 입력해 주세요'); return { a, pay: f.pay.value, file: f.file.files[0]?.name || '—' }; } });
      if (!out) return;
      tr.cells[3].textContent = won2(out.a); tr.cells[4].textContent = out.pay; tr.cells[5].innerHTML = `${esc(out.file)} <button class="btn" data-dlg="receipt">바꾸기</button>`; bindDlg();
      tr.cells[7].innerHTML = '<span class="badge warn">확인 중</span>'; tr.cells[8].textContent = won2(Math.round(out.a * 0.1));
      updateNav(); toast(SCREEN_ONLY);
    },
    async hours(b) {
      const cur = [...document.querySelectorAll('#settings .row')].find((r) => r.firstElementChild?.textContent === '진료시간')?.lastElementChild.firstChild?.textContent.trim() || '';
      const out = await dialog({ title: '진료시간 수정', ok: '저장', body: field('진료시간', `<textarea name="h" rows="3">${esc(cur)}</textarea>`) + '<p class="note">심평원 값과 다르면 환자 화면에 “병원이 직접 수정” 표시가 붙어요.</p>',
        onOk: (f) => f.h.value.trim() || fail('진료시간을 입력해 주세요') });
      if (!out) return; setRow('진료시간', `${esc(out)} <span class="badge">병원 수정</span>`); toast(SCREEN_ONLY);
    },
    async links() {
      const out = await dialog({ title: '홈페이지·SNS 수정', ok: '저장',
        body: field('홈페이지', '<input type="url" name="web" placeholder="https://">') + field('인스타그램', '<input type="url" name="ig" placeholder="https://instagram.com/…">') + '<p class="note">블로그·카페 링크는 넣지 않아요.</p>',
        onOk: (f) => { for (const x of [f.web, f.ig]) if (x.value && !/^https?:\/\//.test(x.value)) fail('주소는 https:// 로 시작해야 해요'); } });
      if (out) toast(SCREEN_ONLY);
    },
    async langs(b) {
      const L = ['영어', '중국어(번체)', '중국어(간체)', '일본어', '베트남어', '몽골어', '러시아어'];
      const out = await dialog({ title: '통역 가능 언어', ok: '저장',
        body: `<div class="opts">${L.map((l) => `<label class="opt"><input type="checkbox" name="l" value="${l}"${/영어|중국어/.test(l) ? ' checked' : ''}><span>${l}</span></label>`).join('')}</div><p class="note">직원이 직접 응대할 수 있는 언어만 골라 주세요. AI 번역 채팅은 따로예요.</p>`,
        onOk: (f) => { const v = [...f.querySelectorAll('input[name=l]:checked')].map((x) => x.value); return v.length ? v : fail('하나 이상 골라 주세요'); } });
      if (!out) return; setRow('직원 응대 언어', `<span class="chips">${out.map((l) => `<span class="chip">${esc(l)}</span>`).join('')}</span>`); markDone(b); toast(SCREEN_ONLY);
    },
    async price(b) {
      const out = await dialog({ title: '가격 안내 입력', ok: '추가',
        body: field('시술', '<input type="text" name="item" placeholder="예: 레이저 토닝 1회" required>')
          + `<div class="pick">${field('최저 (원)', '<input type="number" name="lo" min="0" step="1000">')}${field('최고 (원)', '<input type="number" name="hi" min="0" step="1000">')}</div>`
          + '<p class="note">할인율·기간 한정 가격(이벤트가)은 입력할 수 없어요 (의료광고 규정).</p>',
        onOk: (f) => { const item = f.item.value.trim(), lo = +f.lo.value, hi = +f.hi.value;
          if (!item) fail('시술 이름을 입력해 주세요'); if (/할인|이벤트|%|특가/.test(item)) fail('할인·이벤트 문구는 넣을 수 없어요');
          if (!(lo > 0 && hi > 0)) fail('가격 범위를 입력해 주세요'); if (lo > hi) fail('최저가가 최고가보다 클 수 없어요'); return { item, lo, hi }; } });
      if (!out) return;
      const card = [...document.querySelectorAll('#settings .card h3')].find((h) => h.textContent.startsWith('가격 안내')).parentElement;
      card.querySelector('.note').insertAdjacentHTML('beforebegin', `<div class="row"><span>${esc(out.item)}</span><span>${won2(out.lo)}~${won2(out.hi)}</span></div>`);
      markDone(b); toast(SCREEN_ONLY);
    },
    async faq(b) {
      const out = await dialog({ title: '자주 묻는 질문 추가', ok: '추가',
        body: field('질문 (한국어)', '<input type="text" name="q" required>') + field('답변 (한국어)', '<textarea name="a" rows="3"></textarea>')
          + '<p class="note">저장하면 5개 언어로 번역해 직원이 확인한 뒤 공개돼요. 효과·횟수 같은 의료 판단은 넣지 않아요.</p>',
        onOk: (f) => (f.q.value.trim() && f.a.value.trim()) ? f.q.value.trim() : fail('질문과 답변을 입력해 주세요') });
      if (!out) return; b.insertAdjacentHTML('beforebegin', `<div class="row"><span>${esc(out)}</span><span class="badge gray">번역 대기</span></div>`); toast(SCREEN_ONLY);
    },
    async guide(b) {
      const out = await dialog({ title: '방문 후 안내문 추가', ok: '추가',
        body: field('제목', '<input type="text" name="t" value="붉은기가 오래갈 때 연락 기준">') + field('내용', '<textarea name="c" rows="4" placeholder="예: 3일 넘게 붉은기가 줄지 않으면 사진과 함께 사후관리 채팅으로 알려 주세요"></textarea>'),
        onOk: (f) => f.c.value.trim() || fail('내용을 입력해 주세요') });
      if (!out) return; markDone(b); b.remove(); toast(SCREEN_ONLY);
    },
    async linkToggle(b) {
      const tr = b.closest('tr'), off = b.textContent === '끄기';
      const out = await dialog({ title: `${tr.cells[0].textContent} 링크를 ${off ? '끌까요' : '다시 켤까요'}?`, ok: off ? '끄기' : '켜기', danger: off,
        body: `<p><code>${esc(tr.cells[1].textContent)}</code></p><p class="note">${off ? '끄면 이 링크로 들어온 사람은 병원 상세 대신 일반 목록으로 가요. 지난 집계는 남아요.' : '다시 켜면 이 링크로 들어온 방문·상담이 다시 집계돼요.'}</p>` });
      if (!out) return; b.textContent = off ? '켜기' : '끄기'; tr.style.opacity = off ? .5 : 1; toast(SCREEN_ONLY);
    },
    async linkAdd(b) {
      const out = await dialog({ title: '홍보 링크 만들기', ok: '만들기',
        body: field('채널 이름', '<input type="text" name="ch" placeholder="예: 틱톡, 네이버 카페" required>') + '<p class="note">링크마다 방문·상담·체결이 통계 탭 “유입 경로”에 따로 집계돼요.</p>',
        onOk: (f) => f.ch.value.trim() || fail('채널 이름을 입력해 주세요') });
      if (!out) return;
      const code = Math.random().toString(36).slice(2, 6);
      b.previousElementSibling.querySelector('tbody').insertAdjacentHTML('beforeend', `<tr><td>${esc(out)}</td><td><code>/h/1043?ch=${code}</code></td><td class="r">0</td><td><button class="btn" data-dlg="linkToggle">끄기</button></td></tr>`);
      bindDlg(); toast(SCREEN_ONLY);
    },
  };

  // ---------- 예약 캘린더 (요청 목록과 같은 데이터) ----------
  let DONE_REQS = [], calWeek = 0;  // 방문 완료·미방문 (캘린더 전용), 0 = 이번 주
  const kday = (iso) => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(0, 10);
  const khm = (iso) => new Date(new Date(iso).getTime() + 9 * 3600e3).toISOString().slice(11, 16);
  const EV = { confirmed: ['c', ''], proposed: ['p', '제안 '], pending: ['w', '대기 '], visited: ['v', '✓ '], no_show: ['n', '미방문 '] };
  const calSlot = (r) => r.status === 'pending' ? r.slots[0] : r.confirmed_slot;
  function weekDays() {
    const t = new Date(todayKst() + 'T00:00:00Z'), mon = new Date(t.getTime() - ((t.getUTCDay() + 6) % 7) * 864e5 + calWeek * 7 * 864e5);
    return [...Array(7)].map((_, i) => new Date(mon.getTime() + i * 864e5).toISOString().slice(0, 10));
  }
  function renderCal() {
    const days = weekDays(), today = todayKst(), all = [...REQS, ...DONE_REQS].filter((r) => calSlot(r));
    const md = (d) => `${+d.slice(5, 7)}/${+d.slice(8)}`;
    document.getElementById('calRange').textContent = `${md(days[0])} ~ ${md(days[6])}${calWeek === 0 ? ' · 이번 주' : ''}`;
    document.getElementById('cal').innerHTML = days.map((d, i) => {
      const evs = all.filter((r) => kday(calSlot(r)) === d).sort((a, b) => calSlot(a).localeCompare(calSlot(b)));
      return `<div class="d${d === today ? ' today' : d < today ? ' past' : ''}"><b>${'월화수목금토일'[i]} ${+d.slice(8)}${d === today ? ' · 오늘' : ''}</b>${evs.length
        ? evs.map((r) => `<button type="button" class="ev ${EV[r.status][0]}" data-k="${esc(r.rid || r.id)}" title="${esc(ST[r.status][0])} · ${esc(r.who)}">${EV[r.status][1]}${khm(calSlot(r))} ${esc(r.id)} ${esc(r.title)}</button>`).join('')
        : '<small class="none">예약 없음</small>'}</div>`;
    }).join('');
    document.querySelectorAll('#cal [data-k]').forEach((b) => b.onclick = () => calDetail(all.find((r) => (r.rid || r.id) === b.dataset.k)));
    // 위 숫자 (반복 변경은 근거 데이터가 없어 예시 그대로)
    const thisWeek = (() => { const keep = calWeek; calWeek = 0; const w = weekDays(); calWeek = keep; return w; })();
    const set = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    set('kPend', REQS.filter((r) => r.status === 'pending').length);
    set('kProp', REQS.filter((r) => r.status === 'proposed').length);
    set('kWeek', all.filter((r) => ['confirmed', 'visited', 'no_show'].includes(r.status) && thisWeek.includes(kday(r.confirmed_slot))).length);
  }
  function calDetail(r) {
    const extras = {
      pending: [{ label: '예약 확정', primary: true, onClick: () => bookingAct(r, 'confirm') }, { label: '시간 제안', onClick: () => bookingAct(r, 'propose') }, { label: '거절', onClick: () => bookingAct(r, 'reject') }],
      proposed: [{ label: '다른 시간 다시 제안', onClick: () => bookingAct(r, 'propose') }, { label: '거절', onClick: () => bookingAct(r, 'reject') }],
      confirmed: [{ label: '방문 완료', primary: true, onClick: () => bookingAct(r, 'visited') }, { label: '미방문', onClick: () => bookingAct(r, 'no_show') }],
    }[r.status] || [];
    const when = r.status === 'pending' ? r.slots.map((x, i) => `${esc(kdate(x))} <small>희망 ${i + 1}</small>`).join('<br>') : esc(kdate(r.confirmed_slot));
    return dialog({ title: `${r.id} · ${ST[r.status][0]}`, ok: '닫기', cancel: '', extras,
      body: reqSummary(r) + `<div class="row"><span>${r.status === 'pending' ? '환자 희망 시간' : r.status === 'proposed' ? '제안한 시간' : '예약 시간'}</span><span style="text-align:right">${when}</span></div>`
        + `<div class="row"><span>상태</span><span class="badge ${ST[r.status][1]}">${ST[r.status][0]}</span></div>` });
  }
  document.getElementById('calPrev').onclick = () => { calWeek--; renderCal(); };
  document.getElementById('calNext').onclick = () => { calWeek++; renderCal(); };
  document.getElementById('calToday').onclick = () => { calWeek = 0; renderCal(); };

  // 메뉴 숫자 = 처리할 일. 상담·예약: 대기 요청 / 사후관리: 환자 글에 아직 답 안 한 대화(해결됨 제외)
  // 진료·결제 확인: 결제 금액 API 전이라 DB에 연결되면 숨김 (가짜 숫자 X), 예시 화면에서는 "입력 대기" 줄 수
  // 메뉴 숫자 = 아직 안 열어 본 것. 대화 목록에서 그 항목을 눌러 열면 하나씩 줄어듦 (탭만 옮겨서는 안 줄어듦). 새 요청·새 메시지가 오면 다시 뜸
  // (홈의 "오늘 할 일"·사후관리 KPI는 실제 처리할 건수 그대로)
  const SEEN_KEY = 'md_seen_tabs';
  let SEEN = {};
  try { SEEN = JSON.parse(localStorage.getItem(SEEN_KEY) || '{}'); } catch (e) {}
  const navKey = { booking: (c) => c.id, aftercare: (c) => `${c.tid || c.id}:${c.unread}` };
  function markSeen(tab, item) {
    if (!navKey[tab]) return;
    const k = navKey[tab](item), list = SEEN[tab] || (SEEN[tab] = []);
    if (!list.includes(k)) list.push(k);
    try { localStorage.setItem(SEEN_KEY, JSON.stringify(SEEN)); } catch (e) {}
    updateNav();
  }
  const NAV_ITEMS = {
    booking: () => REQS.filter((r) => r.status === 'pending').map((r) => r.id), // 상담 채팅 목록의 R-… 와 같은 id
    aftercare: () => CHATS.aftercare.filter((c) => c.unread).map(navKey.aftercare), // 같은 대화라도 안 읽은 수가 늘면 새것
  };
  function updateNav() {
    const set = (t, n, show = true) => { const el = document.querySelector(`#tabs button[data-t=${t}] .cnt`); if (el) { el.textContent = n; el.hidden = !show || !n; } };
    const ac = CHATS.aftercare.filter((c) => c.unread).length;
    const unseen = (t) => NAV_ITEMS[t]().filter((k) => !(SEEN[t] || []).includes(k)).length;
    set('booking', unseen('booking'));
    set('aftercare', unseen('aftercare'));
    set('receipt', document.querySelectorAll('#receipt .badge.bad').length, !API.ready);
    for (const id of ['tAc', 'kAcUn']) { const e = document.getElementById(id); if (e) e.textContent = ac; }
  }
  function bindDlg() { document.querySelectorAll('[data-dlg]').forEach((b) => b.onclick = () => DLG[b.dataset.dlg](b)); }
  bindDlg();
  document.getElementById('logoutBtn').onclick = async () => {
    const out = await dialog({ title: '로그아웃할까요?', ok: '로그아웃', body: '<p>이 탭에 저장된 직원 로그인을 지우고 예시 화면으로 돌아가요.</p>' });
    if (!out) return;
    clearStaffToken();
    onLeave();
  };

  // 첫 그리기는 맨 끝에서 (위의 다이얼로그 함수·상수가 모두 정의된 뒤)
  document.querySelectorAll('.chat').forEach((root) => renderChat(root, root.dataset.chat, 0));
  render(); renderReqs(); updateNav(); fromHash(); connectApi();

  return () => {
    cleanups.forEach((f) => f());
    timers.forEach((t) => clearTimeout(t));
  };
}
