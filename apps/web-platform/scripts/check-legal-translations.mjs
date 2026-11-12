// 약관·정책 번역 누락 확인
// 실행: apps/web-platform 에서  node scripts/check-legal-translations.mjs
// src/features/legal/documents.ts 를 esbuild로 묶어 모든 한국어 원문(.ko)을 모으고,
// src/features/legal/translations/{en,zh-TW,zh-CN,vi}.json 에 없는 문자열을 출력한다. 하나라도 없으면 exit 1
// 문서 안에 해당 언어(예: en)가 이미 있는 문자열은 그 언어 파일에서 빠져도 된다
import { build } from 'esbuild';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const legalDir = join(root, 'src/features/legal');
const LANGS = ['en', 'zh-TW', 'zh-CN', 'vi'];

const tmp = mkdtempSync(join(tmpdir(), 'legal-check-'));
let docs;
try {
  const out = join(tmp, 'documents.mjs');
  await build({
    entryPoints: [join(legalDir, 'documents.ts')],
    bundle: true,
    format: 'esm',
    platform: 'node',
    outfile: out,
    logLevel: 'error',
  });
  ({ LEGAL_DOCUMENTS: docs } = await import(pathToFileURL(out).href));
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

// 한국어 원문 → 문서 안에 이미 있는 언어 (같은 원문이 여러 번 나오면 모든 곳에 있어야 인정)
const inline = new Map();
const walk = (o) => {
  if (Array.isArray(o)) return o.forEach(walk);
  if (!o || typeof o !== 'object') return;
  if (typeof o.ko === 'string') {
    const langs = new Set(LANGS.filter((l) => typeof o[l] === 'string' && o[l]));
    const prev = inline.get(o.ko);
    inline.set(o.ko, prev ? new Set([...prev].filter((l) => langs.has(l))) : langs);
  }
  Object.values(o).forEach(walk);
};
walk(docs);

let totalMissing = 0;
for (const lang of LANGS) {
  const file = join(legalDir, 'translations', `${lang}.json`);
  const table = JSON.parse(readFileSync(file, 'utf8'));
  const missing = [...inline].filter(([ko, langs]) => !langs.has(lang) && !(ko in table)).map(([ko]) => ko);
  const unused = Object.keys(table).filter((ko) => !inline.has(ko));
  console.log(`${lang}: ${Object.keys(table).length}개 번역, 누락 ${missing.length}, 원문에 없는 키 ${unused.length}`);
  for (const ko of missing) console.log(`  - 누락: ${ko.slice(0, 80)}`);
  for (const ko of unused) console.log(`  - 안 쓰는 키: ${ko.slice(0, 80)}`);
  totalMissing += missing.length;
}
console.log(`한국어 원문 ${inline.size}개, 누락 합계 ${totalMissing}`);
process.exit(totalMissing > 0 ? 1 : 0);
