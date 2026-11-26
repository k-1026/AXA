// "마이 병원" 탭: 환자 병원 상세 페이지에 나가는 병원 정보를 병원이 직접 고치기 + 회원 등급 바꾸기
// - 병원 정보: 공공데이터(/data/hospitals.json) 값을 기본으로, 고친 값은 features/hospital/overrides.ts 에 저장
//   (지금은 이 브라우저에만 → 같은 브라우저의 환자 화면 /hospitals/:id 에 반영. 백엔드 API가 생기면 그 파일만 교체)
// - 회원 등급: membership.ts (진료·결제 확인 탭의 수수료율이 이 값을 따름)
import { useEffect, useState } from 'react';
import type { TabProps } from './props';
import { Card } from '../ui';
import { readStaffToken } from '../../../../features/staff/staffSession';
import { clearOverride, saveOverride, type HospitalEdit } from '../../../../features/hospital/overrides';
import type { Hospital } from '../../../../features/hospital/types';
import { loadHospitalProfile, refreshHospitalProfile, type HospitalProfile } from '../hospitalProfile';
import { TIERS, saveTier, useTier, type Tier } from '../membership';

const DAYS = ['월', '화', '수', '목', '금', '토', '일'];
const TIMES = Array.from({ length: 33 }, (_, i) => `${String(6 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`); // 06:00~22:00
const LANGS: [string, string][] = [
  ['ko', '한국어'], ['en', '영어'], ['zh-CN', '중국어(간체)'], ['zh-TW', '중국어(번체)'], ['ja', '일본어'], ['vi', '베트남어'], ['ru', '러시아어'], ['mn', '몽골어'], ['th', '태국어'],
];
const RANGE = /^\d{2}:\d{2}~\d{2}:\d{2}$/;

type Form = {
  addr: string; tel: string; email: string; url: string; instagram: string;
  hours: ([string, string] | null)[]; lunchWeek: string; lunchSat: string; rcvWeek: string; rcvSat: string; holidayClosed: boolean;
  parking: string; parkingFee: '' | 'yes' | 'no'; parkingNote: string; languages: string[];
};

const toForm = (h: Hospital): Form => ({
  addr: h.addr ?? '', tel: h.tel ?? '', email: h.email ?? '', url: h.url ?? '', instagram: h.instagram ?? '',
  hours: Array.from({ length: 7 }, (_, i) => h.hours?.[i] ?? null),
  lunchWeek: h.lunchWeek ?? '', lunchSat: h.lunchSat ?? '', rcvWeek: h.rcvWeek ?? '', rcvSat: h.rcvSat ?? '',
  holidayClosed: h.holiday === 'closed',
  parking: h.parking != null ? String(h.parking) : '', parkingFee: h.parkingFee == null ? '' : h.parkingFee ? 'yes' : 'no',
  parkingNote: h.parkingNote ?? '', languages: h.languages ?? ['ko'],
});

function check(f: Form): string {
  if (!f.addr.trim()) return '주소를 입력해 주세요';
  if (f.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) return '이메일 형식을 확인해 주세요';
  for (const [k, v] of [['홈페이지', f.url], ['SNS', f.instagram]] as const) if (v && !/^https?:\/\//.test(v)) return `${k} 주소는 http:// 또는 https:// 로 시작해야 해요`;
  for (const [k, v] of [['평일 점심시간', f.lunchWeek], ['토요일 점심시간', f.lunchSat]] as const) if (v && !RANGE.test(v)) return `${k}은 "13:00~14:00"처럼 써 주세요`;
  if (f.hours.some((x) => x && x[0] >= x[1])) return '진료 시작 시간이 끝나는 시간보다 늦은 요일이 있어요';
  if (f.parking && !(Number(f.parking) >= 0)) return '주차 대수는 숫자로 써 주세요';
  if (!f.languages.length) return '진료·상담 언어를 하나 이상 골라 주세요';
  return '';
}

const toEdit = (f: Form): HospitalEdit => ({
  addr: f.addr.trim(), tel: f.tel.trim(), email: f.email.trim(), url: f.url.trim(), instagram: f.instagram.trim(),
  hours: f.hours, lunchWeek: f.lunchWeek.trim(), lunchSat: f.lunchSat.trim(), rcvWeek: f.rcvWeek.trim(), rcvSat: f.rcvSat.trim(),
  sunday: f.hours[6] ? '' : 'closed', holiday: f.holidayClosed ? 'closed' : '',
  parking: f.parking === '' ? undefined : Number(f.parking), parkingFee: f.parkingFee === '' ? undefined : f.parkingFee === 'yes',
  parkingNote: f.parkingNote.trim(), languages: f.languages,
});

export default function MyHospitalTab(_: TabProps) {
  const [profile, setProfile] = useState<HospitalProfile | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [state, setState] = useState<'loading' | 'ok' | 'none'>('loading');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = () => {
    loadHospitalProfile(readStaffToken()).then((p) => {
      setProfile(p);
      if (p?.hospital) { setForm(toForm(p.hospital)); setState('ok'); } else setState('none');
    });
  };
  useEffect(load, []);

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setForm((f) => (f ? { ...f, [k]: v } : f));
  const setDay = (i: number, v: [string, string] | null) => setForm((f) => (f ? { ...f, hours: f.hours.map((x, j) => (j === i ? v : x)) } : f));

  const save = () => {
    if (!form || !profile?.hospital) return;
    const err = check(form);
    if (err) return setMsg({ ok: false, text: err });
    saveOverride(profile.hospital.id, toEdit(form));
    refreshHospitalProfile();
    setMsg({ ok: true, text: '저장했어요. 환자 병원 상세 페이지에 바로 반영돼요 (지금은 이 브라우저에서만 — 백엔드 연결 전)' });
    load();
  };
  const reset = () => {
    if (!profile?.hospital || !window.confirm('병원이 고친 정보를 모두 지우고 공공데이터 원래 값으로 돌릴까요?')) return;
    clearOverride(profile.hospital.id);
    refreshHospitalProfile();
    setMsg({ ok: true, text: '공공데이터 원래 값으로 돌렸어요' });
    load();
  };

  return (
    <div className="grid">
      {state === 'loading' && <Card title="병원 정보" kind="setup"><p className="mini">불러오는 중…</p></Card>}
      {state === 'none' && <Card title="병원 정보" kind="setup"><p className="note">이 계정의 병원을 병원 목록에서 찾지 못했어요. 다시 로그인해 보거나 운영자에게 문의해 주세요.</p></Card>}

      {form && profile?.hospital && (
        <>
          <section className="card card-wide">
            <header className="card-head">
              <span className="badge badge-setup">설정</span>
              <h3>병원 정보 (환자 병원 상세 페이지에 보여요)</h3>
              <a className="btn-ghost" href={`/hospitals/${encodeURIComponent(profile.hospital.id)}`} target="_blank" rel="noopener noreferrer">환자 화면에서 보기 ↗</a>
            </header>
            <p className="mini">{profile.name} · 공공데이터(심평원) 값을 기본으로 보여 줘요. 고친 칸은 환자 화면에 &ldquo;병원이 직접 수정한 정보 포함&rdquo;으로 표시돼요</p>

            <div className="mh-sections">
              <fieldset className="mh-box">
                <legend>연락처·주소</legend>
                <div className="form-grid">
                  <label className="span2"><span>주소</span><input value={form.addr} onChange={(e) => set('addr', e.target.value)} maxLength={200} /></label>
                  <label><span>전화번호</span><input value={form.tel} onChange={(e) => set('tel', e.target.value)} placeholder="053-000-0000" maxLength={30} /></label>
                  <label><span>이메일</span><input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="contact@example.com" maxLength={100} /></label>
                  <label className="span2"><span>병원 홈페이지</span><input value={form.url} onChange={(e) => set('url', e.target.value)} placeholder="https://" maxLength={300} /></label>
                  <label className="span2"><span>SNS (인스타그램 등)</span><input value={form.instagram} onChange={(e) => set('instagram', e.target.value)} placeholder="https://instagram.com/…" maxLength={300} /></label>
                </div>
              </fieldset>

              <fieldset className="mh-box">
                <legend>진료·상담 언어</legend>
                <div className="mh-langs">
                  {LANGS.map(([code, name]) => (
                    <label key={code} className={`mh-chip${form.languages.includes(code) ? ' is-on' : ''}`}>
                      <input type="checkbox" checked={form.languages.includes(code)}
                        onChange={(e) => set('languages', e.target.checked ? [...form.languages, code] : form.languages.filter((x) => x !== code))} />
                      {name}
                    </label>
                  ))}
                </div>
                <p className="mini">직원이 직접 응대할 수 있는 언어만 골라 주세요. 통역 연결은 메모로 따로 안내하면 좋아요</p>
              </fieldset>

              <fieldset className="mh-box mh-wide">
                <legend>진료시간</legend>
                <div className="mh-hours">
                  {DAYS.map((d, i) => {
                    const v = form.hours[i];
                    return (
                      <div key={d} className={`mh-day${v ? '' : ' is-off'}`}>
                        <b className={i >= 5 ? 'is-weekend' : undefined}>{d}</b>
                        <label className="mh-toggle"><input type="checkbox" checked={!!v} onChange={(e) => setDay(i, e.target.checked ? ['09:00', '18:00'] : null)} /> 진료</label>
                        {v ? (
                          <span className="mh-times">
                            <select value={v[0]} onChange={(e) => setDay(i, [e.target.value, v[1]])} aria-label={`${d} 시작`}>{TIMES.map((x) => <option key={x}>{x}</option>)}</select>
                            <span>~</span>
                            <select value={v[1]} onChange={(e) => setDay(i, [v[0], e.target.value])} aria-label={`${d} 끝`}>{TIMES.map((x) => <option key={x}>{x}</option>)}</select>
                          </span>
                        ) : <span className="mini">휴진</span>}
                      </div>
                    );
                  })}
                </div>
                <div className="form-grid mh-grid4">
                  <label><span>평일 점심시간</span><input value={form.lunchWeek} onChange={(e) => set('lunchWeek', e.target.value)} placeholder="13:00~14:00" /></label>
                  <label><span>토요일 점심시간</span><input value={form.lunchSat} onChange={(e) => set('lunchSat', e.target.value)} placeholder="없으면 비워 두기" /></label>
                  <label><span>평일 접수 마감</span><input value={form.rcvWeek} onChange={(e) => set('rcvWeek', e.target.value)} placeholder="예: 18:30" /></label>
                  <label><span>토요일 접수 마감</span><input value={form.rcvSat} onChange={(e) => set('rcvSat', e.target.value)} placeholder="예: 14:30" /></label>
                </div>
                <label className="mh-toggle"><input type="checkbox" checked={form.holidayClosed} onChange={(e) => set('holidayClosed', e.target.checked)} /> 공휴일 휴진</label>
                <p className="mini">진료시간은 상담 채팅의 대기 시간(진료시간 기준) 계산에도 쓰여요. 환자의 예약 가능 시간 검사(서버)는 백엔드 연결 전이라 아직 원래 값을 써요</p>
              </fieldset>

              <fieldset className="mh-box">
                <legend>주차</legend>
                <div className="form-grid">
                  <label><span>주차 가능 대수</span><input inputMode="numeric" value={form.parking} onChange={(e) => set('parking', e.target.value.replace(/[^\d]/g, ''))} placeholder="예: 10" /></label>
                  <label><span>주차 요금</span>
                    <select value={form.parkingFee} onChange={(e) => set('parkingFee', e.target.value as Form['parkingFee'])}>
                      <option value="">모름·안내 안 함</option><option value="no">무료</option><option value="yes">유료</option>
                    </select>
                  </label>
                  <label className="span2"><span>주차 안내</span><input value={form.parkingNote} onChange={(e) => set('parkingNote', e.target.value)} placeholder="예: 건물 지하 2시간 무료, 진료 후 데스크에서 등록" maxLength={120} /></label>
                </div>
              </fieldset>
            </div>

            {msg && <p className={msg.ok ? 'dlg-toast' : 'dlg-err'} role="status">{msg.text}</p>}
            <div className="day-acts">
              {profile.hospital.edited && <button type="button" className="btn-ghost is-danger" onClick={reset}>공공데이터 값으로 되돌리기</button>}
              <span style={{ flex: 1 }} />
              <button type="button" className="btn-ghost" onClick={() => { setForm(toForm(profile.hospital!)); setMsg(null); }}>고친 것 취소</button>
              <button type="button" className="btn mh-save" onClick={save}>저장</button>
            </div>
          </section>
        </>
      )}

      <MembershipCard />
    </div>
  );
}

function MembershipCard() {
  const tier = useTier();
  const [pick, setPick] = useState<Tier>(tier);
  const [done, setDone] = useState('');
  useEffect(() => setPick(tier), [tier]);
  const change = () => {
    if (pick === tier) return;
    if (!window.confirm(`${TIERS[pick].name}(으)로 바꿀까요?\n수수료율이 ${Math.round(TIERS[tier].rate * 100)}% → ${Math.round(TIERS[pick].rate * 100)}%로 바뀌어요 (진료·결제 확인 탭에 바로 반영)`)) return;
    saveTier(pick);
    setDone(`${TIERS[pick].name}(으)로 바꿨어요 (이 브라우저에 저장 · 백엔드 연결 전)`);
  };
  return (
    <section className="card card-wide">
      <header className="card-head">
        <span className="badge badge-setup">설정</span>
        <h3>회원제</h3>
        <span className="mini">지금: <b>{TIERS[tier].name}</b></span>
      </header>
      <div className="mh-plans" role="radiogroup" aria-label="회원 등급">
        {(Object.keys(TIERS) as Tier[]).map((t) => (
          <label key={t} className={`mh-plan${pick === t ? ' is-on' : ''}`}>
            <input type="radio" name="tier" checked={pick === t} onChange={() => setPick(t)} />
            <span className="mh-plan-top"><b>{TIERS[t].name}</b>{tier === t && <span className="badge badge-live">사용 중</span>}</span>
            <span className="mh-plan-rate">수수료 {Math.round(TIERS[t].rate * 100)}%</span>
            <span className="mini">{TIERS[t].desc}</span>
          </label>
        ))}
      </div>
      <p className="mini">기능은 두 등급이 같아요 (상담·예약·사후관리·통계 모두). 방문이 많은 병원(월 4건 이상)은 프리미엄이 유리해요 · 수수료는 고시 상한(의원 30%) 안 · 금액은 가정값</p>
      {done && <p className="dlg-toast" role="status">{done}</p>}
      <div className="day-acts">
        <button type="button" className="btn mh-save" onClick={change} disabled={pick === tier}>이 등급으로 바꾸기</button>
      </div>
    </section>
  );
}
