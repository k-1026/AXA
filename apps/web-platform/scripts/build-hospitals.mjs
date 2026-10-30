// data/interim/영업정보/daegu_hospital_hours.csv → public/data/hospitals.json
// 지도에 필요한 열만 남긴다. 원본 데이터는 수정하지 않는다.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '../../..');
const csvPath = resolve(repo, 'data/interim/영업정보/daegu_hospital_hours.csv');
const metaPath = resolve(repo, 'data/raw/영업정보/daegu_hospital_hours.json');
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

const rows = parseCsv(readFileSync(csvPath, 'utf8').replace(/^﻿/, ''));
const meta = JSON.parse(readFileSync(metaPath, 'utf8')).meta;

const items = rows
  .filter((r) => r.XPos && r.YPos)
  .map((r) => {
    const depts = [];
    if (r.has_dermatology === 'Y') depts.push('dermatology');
    if (r.has_plastic_surgery === 'Y') depts.push('plastic');
    if (r.clCdNm.startsWith('치과')) depts.push('dental');
    return {
      id: r.ykiho,
      name: r.yadmNm,
      type: r.clCdNm,
      district: r.sgguCdNm,
      addr: r.addr,
      tel: r.telno,
      lat: Number(r.YPos),
      lng: Number(r.XPos),
      depts,
    };
  });

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(
  outPath,
  JSON.stringify({ meta: { source: meta.source, fetchedAt: meta.fetchedAt }, items }),
);
console.log(`hospitals.json: ${items.length}곳`);
