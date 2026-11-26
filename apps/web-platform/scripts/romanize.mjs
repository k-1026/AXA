// 병원 이름 → 영어 이름 (기준: docs/번역-표기-기준.md 2장)
// 우선순위: ① 병원 공식 영문명(메디컬코리아 등록 목록, 한국어 이름과 맞는지 확인한 것만) → ② 자동 표기
// 자동 표기 = 고유 이름(국어의 로마자 표기법, 낱말 단위로 붙여 씀) + 진료과 + 기관 종류
// 예: 고운미피부과의원 → Gounmi Dermatology Clinic, 계명대학교동산병원 → Gyemyeong University Dongsan Hospital
const INITIAL = ['g', 'kk', 'n', 'd', 'tt', 'r', 'm', 'b', 'pp', 's', 'ss', '', 'j', 'jj', 'ch', 'k', 't', 'p', 'h'];
const VOWEL = ['a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 'wae', 'oe', 'yo', 'u', 'wo', 'we', 'wi', 'yu', 'eu', 'ui', 'i'];
const FINAL = ['', 'k', 'k', 'k', 'n', 'n', 'n', 't', 'l', 'k', 'm', 'l', 'l', 'l', 'p', 'l', 'm', 'p', 'p', 't', 't', 'ng', 't', 't', 'k', 't', 'p', 't'];

const parts = (ch) => {
  const c = ch.codePointAt(0) - 0xac00;
  return [Math.floor(c / 588), Math.floor((c % 588) / 28), c % 28];
};
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);

/** 한글 낱말 → 로마자 한 낱말 (붙여 씀). 받침 ㄹ + 초성 ㄹ은 ll (신라 → Silla). 소리 동화는 반영하지 않음 */
export function romanizeWord(word) {
  let out = '';
  let prevFinal = 0;
  for (const ch of word) {
    if (!/[가-힣]/.test(ch)) {
      out += ch;
      prevFinal = 0;
      continue;
    }
    const [i, v, f] = parts(ch);
    const initial = i === 5 && prevFinal === 8 ? 'l' : INITIAL[i]; // ㄹㄹ → ll
    out += initial + VOWEL[v] + FINAL[f];
    prevFinal = f;
  }
  return cap(out);
}

/** 띄어쓰기 단위로 낱말마다 로마자 (음절마다 띄우지 않음) */
export function romanize(text) {
  return text.split(/\s+/).filter(Boolean).map(romanizeWord).join(' ');
}

// 긴 이름부터 찾는다 (정형외과가 외과로 잘리지 않게)
const INSTITUTIONS = [
  ['대학교병원', 'University Hospital'],
  ['요양병원', 'Long-term Care Hospital'],
  ['한방병원', 'Korean Medicine Hospital'],
  ['아동병원', "Children's Hospital"],
  ['치과병원', 'Dental Hospital'],
  ['치과의원', 'Dental Clinic'],
  ['한의원', 'Korean Medicine Clinic'],
  ['의료원', 'Medical Center'],
  ['보건지소', 'Public Health Branch'],
  ['보건소', 'Public Health Center'],
  ['병원', 'Hospital'],
  ['의원', 'Clinic'],
];
const DEPARTMENTS = [
  ['마취통증의학과', 'Pain Medicine'],
  ['정신건강의학과', 'Psychiatry'],
  ['소아청소년과', 'Pediatrics'],
  ['치과교정과', 'Orthodontics'],
  ['통증의학과', 'Pain Medicine'],
  ['재활의학과', 'Rehabilitation Medicine'],
  ['가정의학과', 'Family Medicine'],
  ['영상의학과', 'Radiology'],
  ['비뇨의학과', 'Urology'],
  ['비뇨기과', 'Urology'],
  ['이비인후과', 'ENT'],
  ['성형외과', 'Plastic Surgery'],
  ['정형외과', 'Orthopedics'],
  ['신경외과', 'Neurosurgery'],
  ['흉부외과', 'Thoracic Surgery'],
  ['산부인과', 'OB/GYN'],
  ['소아과', 'Pediatrics'],
  ['피부과', 'Dermatology'],
  ['신경과', 'Neurology'],
  ['내과', 'Internal Medicine'],
  ['외과', 'Surgery'],
  ['안과', 'Eye'],
];

/** 한국어 이름 → { brand: 고유 이름 로마자, dept, inst } */
function split(name) {
  let rest = name
    .replace(/^\((재|의|사|학|주)\)/, '') // 법인 표시
    .replace(/^의료법인\s*\S*?재단\s*/, '') // "의료법인 ○○의료재단" 앞머리
    .replace(/\([一-鿿]+\)/g, '') // 한자 병기
    .replace(/\([A-Za-z]+\)/g, '') // 영문 병기 "(H)" — 공식 영문명이 없으면 아래 MANUAL에서
    .trim();
  // "아트너의원 죽전점" → 지점명은 고유 이름 쪽에 붙인다
  let branch = '';
  const m = rest.match(/^(.*(?:의원|병원))\s*([가-힣]+)점$/);
  if (m) {
    rest = m[1];
    branch = m[2];
  }
  const cut = (table) => {
    const hit = table.find(([ko]) => rest.endsWith(ko));
    if (!hit) return undefined;
    rest = rest.slice(0, -hit[0].length).trim();
    return hit[1];
  };
  const inst = cut(INSTITUTIONS);
  const dept = inst ? cut(DEPARTMENTS) : undefined;
  // 이름 중간의 '대학교'는 University로 (계명대학교동산병원 → Gyemyeong University Dongsan)
  const words = `${rest} ${branch}`
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .flatMap((w) => w.split(/(대학교)/).filter(Boolean))
    .map((w) => (w === '대학교' ? 'University' : romanizeWord(w)));
  return { brand: words.join(' '), dept, inst };
}

/** ② 자동 표기 */
export function englishName(name) {
  const { brand, dept, inst } = split(name);
  return [brand, dept, inst].filter(Boolean).join(' ');
}

// 사람이 정한 영어 이름 (공식 영문명이 약어뿐 · 띄어쓰기 없음 · 같은 브랜드의 공식 표기가 따로 있음)
// 바탕: 메디컬코리아 등록 목록 name_en
const MANUAL = {
  경북대학교병원: 'Kyungpook National University Hospital', // 공식 목록에는 약어 KNUH만
  고려에이치한방병원: 'Korea H Korean Medicine Hospital', // 공식: KOREA H HOSPITAL OF KOREAN MEDICINE
  대구보건대학교병원: 'Daegu Health College Hospital', // 공식: DaeguHealthCollege Hospital
  동성로아트너의원: 'Artner Clinic Dongseongro', // 공식 목록은 다른 이름(sangsangclinic), 같은 브랜드 공식 표기 Artner
};

// 공식 영문명이 지금 한국어 이름과 다른 병원을 가리키는 것 (예전 등록명 등) → 자동 표기
const REJECT_OFFICIAL = new Set([
  '리브의원', // 공식: PPEUM CLINIC
  '픽미의원', // 공식: vands clinic
  '상연의원', // 공식: Dr.Designer Clinic Daegu Jukjeon
]);

// 공식 영문명 정리: 대소문자 맞춤, 흔한 오타, 붙어 있는 기관 종류 띄우기, 한방 표기 통일, 지역·괄호 꼬리 삭제, 기관 종류가 없으면 붙임
const TYPO = [
  [/\bMeddicine\b/gi, 'Medicine'], [/\bOrietnal\b/gi, 'Oriental'], [/\bHosptal\b/gi, 'Hospital'],
  [/\bClinnic\b/gi, 'Clinic'], [/\bClininc\b/gi, 'Clinic'], [/\bDermatologic\b/gi, 'Dermatology'],
];
// 대문자 그대로 둘 약어
const KEEP_UPPER = new Set(['ENT', 'E.N.T', 'FM', 'BL', 'BM', 'CU', 'CIM', 'VB', 'SEN', 'CHA', 'MC', 'FNB']);
const SMALL = new Set(['of', 'and', 'the']);
const titleWord = (w) => w.toLowerCase().replace(/(^|[-'(&.])([a-z])/g, (_, p, c) => p + c.toUpperCase()).replace(/'S\b/g, "'s");
function tidyOfficial(raw, inst) {
  let s = raw
    .replace(/\([^)]*\)/g, ' ') // 괄호 설명 "(Daegu)" "(Comprehensive…)"
    .replace(/([a-z])(hospital|clinic|dental|dermatology)\b/gi, '$1 $2') // hanmihospital → hanmi hospital
    .replace(/([a-z])(Clinic|Dermatology)\b/g, '$1 $2') // JrynClinic → Jryn Clinic
    .replace(/\s+/g, ' ')
    .trim();
  for (const [re, to] of TYPO) s = s.replace(re, to);
  s = s
    .split(' ')
    .map((w, i) => {
      const up = w.toUpperCase();
      if (KEEP_UPPER.has(up)) return up === 'FNB' ? 'FnB' : up;
      if (up === 'ENT') return 'ENT';
      if (i > 0 && SMALL.has(w.toLowerCase())) return w.toLowerCase();
      const allCaps = w === up && /[A-Z]{2,}/.test(w);
      const lowerStart = /^[a-z]/.test(w);
      return allCaps || lowerStart ? titleWord(w) : w; // HwaJubMong 같은 원래 대소문자는 그대로
    })
    .join(' ');
  // 지역·지점 꼬리 "Daegu"는 이름에 필요 없음 (Liting Plastic Surgery Daegu → Liting Plastic Surgery)
  s = s.replace(/,?\s+Daegu$/i, '');
  // 한방: Oriental Medical/Medicine · Korean Medical → Korean Medicine (기준 5-1)
  s = s
    .replace(/\bOriental Medic(al|ine)\b/gi, 'Korean Medicine')
    .replace(/\bOriental Clinic\b/gi, 'Korean Medicine Clinic')
    .replace(/\bKorean ?Medical\b/gi, 'Korean Medicine')
    .replace(/\bHaniwon\b/gi, 'Korean Medicine Clinic');
  // 기관 종류 단어가 없으면 한국어 이름의 기관 종류를 붙임 (Gounmi Dermatology → Gounmi Dermatology Clinic)
  if (inst && !/\b(Clinic|Hospital|Center|Centre)\b/i.test(s)) s = `${s} ${inst.split(' ').at(-1)}`;
  return s;
}

/**
 * 화면에 쓸 영어 이름과 출처 (기준 2-1).
 * 공식 영문명은 외래어 브랜드(더블랙 → THE BLACK)가 많아 소리 비교로 거르면 맞는 이름까지 버려진다 →
 * 기본은 공식 영문명, 지금 한국어 이름과 다른 병원 이름인 것만 REJECT_OFFICIAL로 뺀다 (사람이 확인해 추가)
 * @returns {{ nameEn: string, source: 'manual' | 'official' | 'auto' }}
 */
export function chooseEnglishName(nameKo, officialEn) {
  if (MANUAL[nameKo]) return { nameEn: MANUAL[nameKo], source: 'manual' };
  const { inst } = split(nameKo);
  const off = (officialEn ?? '').trim();
  const abbrOnly = /^[A-Z]{2,4}$/.test(off); // KNUH 같은 약어만 (SUAVEL·FARBE는 이름)
  if (off && !abbrOnly && !REJECT_OFFICIAL.has(nameKo)) {
    return { nameEn: tidyOfficial(off, inst), source: 'official' };
  }
  return { nameEn: englishName(nameKo), source: 'auto' };
}
