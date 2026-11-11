// 병원 이름 → 영어 이름: 발음 표기(국어의 로마자 표기법, 음절 단위) + 진료과·기관 종류 번역
// 예: 신세계안과의원 → Sin Se Gye Eye Clinic
const INITIAL = ['g', 'kk', 'n', 'd', 'tt', 'r', 'm', 'b', 'pp', 's', 'ss', '', 'j', 'jj', 'ch', 'k', 't', 'p', 'h'];
const VOWEL = ['a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 'wae', 'oe', 'yo', 'u', 'wo', 'we', 'wi', 'yu', 'eu', 'ui', 'i'];
const FINAL = ['', 'k', 'k', 'k', 'n', 'n', 'n', 't', 'l', 'k', 'm', 'l', 'l', 'l', 'p', 'l', 'm', 'p', 'p', 't', 't', 'ng', 't', 't', 'k', 't', 'p', 't'];

function syllable(ch) {
  const code = ch.codePointAt(0) - 0xac00;
  const text = INITIAL[Math.floor(code / 588)] + VOWEL[Math.floor((code % 588) / 28)] + FINAL[code % 28];
  return text[0].toUpperCase() + text.slice(1);
}

export function romanize(text) {
  return (text.match(/[가-힣]|[^가-힣\s]+/g) ?? [])
    .map((part) => (/[가-힣]/.test(part) ? syllable(part) : part))
    .join(' ');
}

// 긴 이름부터 찾는다 (정형외과가 외과로 잘리지 않게)
const INSTITUTIONS = [
  ['대학교병원', 'University Hospital'],
  ['요양병원', 'Long-term Care Hospital'],
  ['한방병원', 'Korean Medicine Hospital'],
  ['아동병원', "Children's Hospital"],
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

export function englishName(name) {
  let rest = name
    .replace(/^\((재|의|사|학|주)\)/, '') // 법인 표시
    .replace(/\([一-鿿]+\)/g, '') // 한자 병기
    .trim();
  // "아트너의원 죽전점" → 지점명은 발음 표기 쪽에 붙인다
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
  return [romanize(`${rest} ${branch}`), dept, inst].filter(Boolean).join(' ');
}
