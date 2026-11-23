// data/interim/영업정보/*.csv → public/data/hospitals.json
// 피부과·성형외과·내과·안과 병원만, 한국어 가나다순으로 저장한다. 원본 데이터는 수정하지 않는다.
// **등록 외국인환자 유치의료기관만** 내보낸다 (백엔드 결정 21, 복지부·진흥원 회신 2026-11-17:
// 외국어 병원 정보 웹도 유치행위로 평가될 수 있음 → 미등록 병원 노출 X). 백엔드 GET /hospitals와 같은 기준
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { englishName } from './romanize.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '../../..');
const interim = resolve(repo, 'data/interim/영업정보');
const raw = resolve(repo, 'data/raw/영업정보');
const outPath = resolve(here, '../public/data/hospitals.json');

// 따옴표 안의 쉼표·줄바꿈을 처리하는 최소 CSV 파서
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (c !== '\r') field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const [header, ...body] = rows;
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ''])));
}

const readCsv = (name, dir = interim) => parseCsv(readFileSync(resolve(dir, name), 'utf8').replace(/^﻿/, ''));
const readMeta = (name) => JSON.parse(readFileSync(resolve(raw, name), 'utf8')).meta;

const hours = readCsv('daegu_hospital_hours.csv');
const basics = new Map(readCsv('daegu_hospitals.csv').map((r) => [r.ykiho, r]));
// 폐업 교차검증(심평원·행안부) 결과가 '정상'이 아닌 곳(폐업·미확인)은 뺀다
// 방법: research/의료관광/병원-폐업-교차검증.md
const excluded = new Set(
  readCsv('daegu_hospital_status.csv', resolve(repo, 'data/processed'))
    .filter((r) => r.verdict !== '정상')
    .map((r) => r.ykiho),
);
// 등록 유치의료기관 (요양기관 기호로 맞춘 것만). 파일이 없으면 아무 병원도 내보내지 않는다 (미등록 노출 방지)
const registeredPath = resolve(repo, 'data/processed/daegu_registered_institutions.csv');
const registeredRows = existsSync(registeredPath) ? readCsv('daegu_registered_institutions.csv', resolve(repo, 'data/processed')) : [];
const registered = existsSync(registeredPath) ? new Set(registeredRows.map((r) => r.ykiho).filter(Boolean)) : null;
if (!registered) {
  console.warn(
    '⚠ data/processed/daegu_registered_institutions.csv 없음 → 병원 0곳으로 저장 (미등록 병원 노출 방지).\n' +
      '  받기: git restore --source origin/research-data -- data/processed/daegu_registered_institutions.csv',
  );
}
// 등록 유치기관 진료시간 직접 채움 (2026-11-18, data/etl/build_registered_hours.py 결과)
// 심평원 API에 없는 요일을 채움. override=Y는 검증에서 API 값이 틀린 것으로 확인돼 API 값도 바꿈 (백엔드 loader와 같은 규칙)
const manualPath = resolve(repo, 'data/processed/daegu_hours_manual.csv');
const manualHours = new Map(
  existsSync(manualPath) ? readCsv('daegu_hours_manual.csv', resolve(repo, 'data/processed')).map((r) => [r.ykiho, r]) : [],
);
// 10/28에 사람이 확인한 값 (중구·수성구 직접 채움, 수성구 외국인환자 유치기관). 평일·토·일 칸이 "HH:MM-HH:MM"일 때만 씀
const oldManual = new Map();
for (const [name, ok] of [
  ['manual_fill_junggu_suseonggu.csv', (r) => r.fill_status === 'filled'],
  ['suseong_foreign_patient_facilities.csv', (r) => r.ykiho && r.weekday_hours],
]) {
  if (!existsSync(resolve(interim, name))) continue;
  for (const r of readCsv(name).filter(ok)) oldManual.set(r.ykiho, r);
}
// 홈페이지·인스타그램 (팀 수집 파일에서 사이트 병원과 맞는 곳만, 블로그·네이버 제외)
const links = new Map(readCsv('daegu_hospital_links.csv', resolve(repo, 'data/processed')).map((r) => [r.ykiho, r]));
// 대표사진 주소 (팀 수집 파일을 요양기관 기호로 맞춘 것). 사진 파일은 저장하지 않고 원래 주소로 표시
// 프로토타입용 임시 (2026-11-04). 광고성 이미지가 섞여 있고 이용 조건 미확인 → 정식 공개 전에 교체
const photos = new Map(readCsv('daegu_hospital_photos.csv', resolve(repo, 'data/processed')).map((r) => [r.ykiho, r.photo]));

// 진료과 판정
// - 피부과·성형외과: 심평원 진료과목 코드 (14, 08)
// - 내과·안과: 진료과목 코드를 아직 수집하지 않아서 임시로 "의원·병원 이름에 '내과'·'안과'" 기준
//   → 내과·안과가 있는 종합병원 등은 빠짐. 진료과목 01·12 수집 후 교체
// 여러 진료과면 병원 이름에 들어 있는 진료과를 맨 앞에 둔다 (지도 색상 기준)
const DEPT_NAMES = { dermatology: '피부과', plastic: '성형외과', internal: '내과', ophthalmology: '안과' };
function departments(r) {
  const depts = [];
  if (r.has_dermatology === 'Y') depts.push('dermatology');
  if (r.has_plastic_surgery === 'Y') depts.push('plastic');
  const medical = !r.clCdNm.startsWith('치과') && !r.clCdNm.startsWith('한');
  if (medical && r.yadmNm.includes('내과')) depts.push('internal');
  if (medical && r.yadmNm.includes('안과')) depts.push('ophthalmology');
  depts.sort((a, b) => r.yadmNm.includes(DEPT_NAMES[b]) - r.yadmNm.includes(DEPT_NAMES[a]));
  // 4개 진료과가 아닌 등록 유치기관(치과·한방·종합병원 등)은 "기타"
  return depts.length ? depts : ['other'];
}

// 한 요일의 진료시간: 심평원 API → 직접 채움(daegu_hours_manual) → 10/28 직접 채움 순
const RANGE = /^(\d\d:\d\d)-(\d\d:\d\d)$/;
const fromRange = (v) => {
  const m = RANGE.exec((v ?? '').trim());
  return m && m[1] < m[2] ? [m[1], m[2]] : null;
};
function weekOf(r) {
  const api = DAYS.map((d) => {
    const start = hhmm(r[`trmt${d}Start`]);
    const end = hhmm(r[`trmt${d}End`]);
    return start && end ? [start, end] : null;
  });
  const m = manualHours.get(r.ykiho);
  if (m) {
    const override = m.override?.toUpperCase() === 'Y';
    return DAYS.map((d, i) => {
      const v = m[d.toLowerCase()];
      if (override && v === '휴진') return null;
      return (override ? fromRange(v) ?? api[i] : api[i] ?? fromRange(v));
    });
  }
  const o = oldManual.get(r.ykiho);
  if (o && !api.some(Boolean)) {
    // "09:00-18:00 (외래 기본)"처럼 설명이 붙은 칸은 앞의 시간만 씀. 요일별로 다른 문장("월·금 …/화·수·목 …")은 쓰지 않음
    const first = (v) => (/^\d\d:\d\d-\d\d:\d\d(\s*\(.*\))?$/.test((v ?? '').trim()) ? fromRange(v.trim().slice(0, 11)) : null);
    const wk = first(o.weekday_hours);
    if (wk) return [wk, wk, wk, wk, wk, first(o.sat_hours), first(o.sun_hours)];
    // "월·수·목 09:00-19:00 / 화·금 09:00-20:30" → 요일별
    const byDay = Array(5).fill(null);
    for (const part of (o.weekday_hours ?? '').split('/')) {
      const m = /^\s*([월화수목금·]+)\s+(\d\d:\d\d-\d\d:\d\d)\s*$/.exec(part);
      if (m) for (const d of m[1].split('·')) if ('월화수목금'.includes(d) && d) byDay['월화수목금'.indexOf(d)] = fromRange(m[2]);
    }
    if (byDay.some(Boolean)) return [...byDay, first(o.sat_hours), first(o.sun_hours)];
  }
  return api;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const hhmm = (v) => (/^\d{4}$/.test(v) ? `${v.slice(0, 2)}:${v.slice(2)}` : '');
// "13시00분~14시00분" → "13:00~14:00", 나머지 표기는 그대로
const tidyTime = (v) => v.replace(/(\d{1,2})시\s*(\d{2})분/g, (_, h, m) => `${h.padStart(2, '0')}:${m}`).trim();
// API 휴진 표기 ("전부 휴진"·"휴진"·"휴무" 등) → closed, 그 밖의 문장은 원문 유지
const closedNote = (v) => {
  const s = v.replace(/\s/g, '');
  if (!s) return undefined;
  return /^(전부|종일)?(휴진|휴무)$/.test(s) ? 'closed' : v.trim();
};
const yn = (v) => (v === 'Y' ? true : v === 'N' ? false : undefined);
// 심평원 홈페이지 값 중 네이버 블로그·카페·모두는 홈페이지로 넣지 않는다
const url = (v) => {
  const s = v.trim();
  if (!s || /naver\.com|modoo\.at/i.test(s)) return undefined;
  return /^https?:\/\//i.test(s) ? s : `http://${s}`;
};

// "(재)", "(의)" 같은 괄호는 정렬에서 무시
const collator = new Intl.Collator('ko', { ignorePunctuation: true });

// 심평원 목록에서 찾지 못한 등록 유치기관 (메디컬코리아에는 있음, 2026-11-18).
// 같은 도로명 주소 건물의 심평원 좌표를 빌려 지도에 표시하고, 나머지는 메디컬코리아 영문 정보만 보여 준다
const NO_HIRA = {
  'M-2024-03-08-7710': { addr: '대구광역시 중구 동성로1길 77', district: '중구', type: '의원', depts: ['plastic'] },
};
const hoursById = new Map(hours.map((r) => [r.ykiho, r]));
function noHiraItem(reg) {
  const extra = NO_HIRA[reg.registration_no];
  const near = extra && hours.find((h) => h.addr.startsWith(`${extra.addr},`) || h.addr === extra.addr);
  if (!near) {
    console.warn(`⚠ 심평원·좌표 없음: ${reg.registration_no} ${reg.name_en}`);
    return null;
  }
  return {
    id: reg.registration_no,
    name: reg.name_en,
    nameEn: reg.name_en,
    type: extra.type,
    district: extra.district,
    addr: extra.addr,
    tel: reg.tel && !reg.tel.includes('*') ? reg.tel : undefined,
    url: reg.website ? url(reg.website) : undefined,
    lat: Number(near.YPos),
    lng: Number(near.XPos),
    depts: extra.depts,
    // 심평원 기호가 없는 곳은 사진 파일에 등록번호로 넣어 둠
    photo: photos.get(reg.registration_no),
  };
}

// 메디컬코리아 등록 유치의료기관 161곳 전부 (진료시간이 없으면 빈칸으로 표시)
const items = registeredRows
  .map((reg) => (reg.ykiho ? hoursById.get(reg.ykiho) : null) ?? noHiraItem(reg))
  .filter(Boolean)
  .filter((r) => r.id || (r.XPos && r.YPos && !excluded.has(r.ykiho)))
  .map((r) => (r.id ? { item: r } : { r, depts: departments(r), week: weekOf(r) }))
  .map(({ item, r, depts, week }) => {
    if (item) return item;
    const b = basics.get(r.ykiho) ?? {};
    const link = links.get(r.ykiho);
    const m = manualHours.get(r.ykiho);
    const name = r.yadmNm.replace(/&amp;/g, '&');
    // 빈 값은 저장하지 않음 → 화면에서 빈칸
    return {
      id: r.ykiho,
      name,
      nameEn: englishName(name),
      type: r.clCdNm,
      district: r.sgguCdNm.replace(/^대구/, ''),
      addr: r.addr,
      tel: r.telno || undefined,
      url: link?.homepage || url(b.hospUrl ?? ''),
      instagram: link?.instagram || undefined,
      photo: photos.get(r.ykiho),
      lat: Number(r.YPos),
      lng: Number(r.XPos),
      depts,
      hours: week.some(Boolean) ? week : undefined,
      lunchWeek: tidyTime(r.lunchWeek) || m?.lunch_week || undefined,
      lunchSat: tidyTime(r.lunchSat) || m?.lunch_sat || undefined,
      rcvWeek: tidyTime(r.rcvWeek) || undefined,
      rcvSat: tidyTime(r.rcvSat) || undefined,
      sunday: closedNote(r.noTrmtSun) ?? (m?.sun === '휴진' ? 'closed' : undefined),
      holiday: closedNote(r.noTrmtHoli) ?? closedNote(m?.holiday ?? ''),
      emergencyDay: yn(r.emyDayYn),
      emergencyNight: yn(r.emyNgtYn),
      parking: r.parkQty ? Number(r.parkQty) : undefined,
      parkingFee: yn(r.parkXpnsYn),
    };
  })
  .sort((a, b) => collator.compare(a.name, b.name));

// 시연용 가상 병원 (is_demo). 백엔드 seed_demo_shared.py와 같은 파일을 읽어 DB와 값이 같음
// 실제 병원에는 예시 일정·예약을 붙이지 않고 이 병원으로만 시연 (compliance 2-6)
const demoPath = resolve(repo, 'data/processed/demo/demo_hospital.json');
if (existsSync(demoPath)) {
  const d = JSON.parse(readFileSync(demoPath, 'utf8'));
  const strip = (s) => s.replace(/\s*\((가상|Demo)\)\s*$/, ''); // "시연용" 표시는 화면에서 언어별로 붙임
  const week = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map((k) => d.hours[k] ?? null);
  items.push({
    id: d.ykiho,
    demo: true,
    name: strip(d.name_ko),
    nameEn: strip(d.name_en),
    type: d.type_name_ko,
    district: d.sggu.replace(/^대구/, ''),
    addr: d.addr_ko,
    lat: d.lat,
    lng: d.lng,
    depts: d.depts,
    hours: week,
    lunchWeek: d.lunch ? `${d.lunch[0]}~${d.lunch[1]}` : undefined,
    sunday: week[6] ? undefined : 'closed',
  });
  items.sort((a, b) => collator.compare(a.name, b.name));
}

const basicMeta = readMeta('daegu_hospitals.json');
const hoursMeta = readMeta('daegu_hospital_hours.json');

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(
  outPath,
  JSON.stringify({
    meta: {
      source: [basicMeta.source, hoursMeta.source].join(' + '),
      fetchedAt: hoursMeta.fetchedAt,
    },
    items,
  }),
);
console.log(`hospitals.json: ${items.length}곳`);
