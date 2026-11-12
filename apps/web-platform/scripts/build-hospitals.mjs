// data/interim/영업정보/*.csv → public/data/hospitals.json
// 피부과·성형외과·내과·안과 병원만, 한국어 가나다순으로 저장한다. 원본 데이터는 수정하지 않는다.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
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
  return depts.sort((a, b) => r.yadmNm.includes(DEPT_NAMES[b]) - r.yadmNm.includes(DEPT_NAMES[a]));
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

const items = hours
  .map((r) => ({ r, depts: departments(r) }))
  .filter(({ r, depts }) => depts.length > 0 && r.XPos && r.YPos && !excluded.has(r.ykiho))
  .map(({ r, depts }) => {
    const b = basics.get(r.ykiho) ?? {};
    const link = links.get(r.ykiho);
    const name = r.yadmNm.replace(/&amp;/g, '&');
    const week = DAYS.map((d) => {
      const start = hhmm(r[`trmt${d}Start`]);
      const end = hhmm(r[`trmt${d}End`]);
      return start && end ? [start, end] : null;
    });
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
