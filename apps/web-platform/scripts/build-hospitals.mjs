// data/interim/영업정보/*.csv → public/data/hospitals.json
// 피부과·성형외과·내과·치과 병원만, 한국어 가나다순으로 저장한다. 원본 데이터는 수정하지 않는다.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

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

const readCsv = (name) => parseCsv(readFileSync(resolve(interim, name), 'utf8').replace(/^﻿/, ''));
const readMeta = (name) => JSON.parse(readFileSync(resolve(raw, name), 'utf8')).meta;

const hours = readCsv('daegu_hospital_hours.csv');
const basics = new Map(readCsv('daegu_hospitals.csv').map((r) => [r.ykiho, r]));

// 진료과 판정
// - 피부과·성형외과: 심평원 진료과목 코드 (14, 08)
// - 치과: 종별이 치과병원·치과의원
// - 내과: 진료과목 코드를 아직 수집하지 않아서 임시로 "의원·병원 이름에 '내과'" 기준
//   → 내과가 있는 종합병원 등은 빠짐. 진료과목 01 수집 후 교체
function departments(r) {
  const depts = [];
  if (r.has_dermatology === 'Y') depts.push('dermatology');
  if (r.has_plastic_surgery === 'Y') depts.push('plastic');
  const medical = !r.clCdNm.startsWith('치과') && !r.clCdNm.startsWith('한');
  if (medical && r.yadmNm.includes('내과')) depts.push('internal');
  if (r.clCdNm.startsWith('치과')) depts.push('dental');
  return depts;
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
const url = (v) => {
  const s = v.trim();
  if (!s) return undefined;
  return /^https?:\/\//i.test(s) ? s : `http://${s}`;
};

// "(재)", "(의)" 같은 괄호는 정렬에서 무시
const collator = new Intl.Collator('ko', { ignorePunctuation: true });

const items = hours
  .map((r) => ({ r, depts: departments(r) }))
  .filter(({ r, depts }) => depts.length > 0 && r.XPos && r.YPos)
  .map(({ r, depts }) => {
    const b = basics.get(r.ykiho) ?? {};
    const week = DAYS.map((d) => {
      const start = hhmm(r[`trmt${d}Start`]);
      const end = hhmm(r[`trmt${d}End`]);
      return start && end ? [start, end] : null;
    });
    // 빈 값은 저장하지 않음 → 화면에서 빈칸
    return {
      id: r.ykiho,
      name: r.yadmNm,
      type: r.clCdNm,
      district: r.sgguCdNm.replace(/^대구/, ''),
      addr: r.addr,
      tel: r.telno || undefined,
      url: url(b.hospUrl ?? ''),
      lat: Number(r.YPos),
      lng: Number(r.XPos),
      depts,
      hours: week.some(Boolean) ? week : undefined,
      lunchWeek: tidyTime(r.lunchWeek) || undefined,
      lunchSat: tidyTime(r.lunchSat) || undefined,
      rcvWeek: tidyTime(r.rcvWeek) || undefined,
      rcvSat: tidyTime(r.rcvSat) || undefined,
      sunday: closedNote(r.noTrmtSun),
      holiday: closedNote(r.noTrmtHoli),
      emergencyDay: yn(r.emyDayYn),
      emergencyNight: yn(r.emyNgtYn),
      parking: r.parkQty ? Number(r.parkQty) : undefined,
      parkingFee: yn(r.parkXpnsYn),
    };
  })
  .sort((a, b) => collator.compare(a.name, b.name));

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
