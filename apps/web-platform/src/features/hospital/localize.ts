// 병원 이름·주소를 화면 언어로 (데이터에는 한국어 이름·주소와 영어 이름만 있음)
// - 이름: 영어 이름(scripts/romanize.mjs englishName) = "발음 표기 + 진료과 + 기관 종류" →
//   중국어·베트남어는 진료과·기관 종류만 번역하고 발음 표기는 그대로 (고유 이름을 지어내지 않음)
// - 주소: 도로명 주소를 국어의 로마자 표기법(음절 단위, romanize.mjs와 같은 표)으로 옮김.
//   중국어는 시·구를 한자로. 정확한 위치 확인용 한국어 원문은 화면에서 함께 보여 준다

type Lang = 'zh-TW' | 'zh-CN' | 'vi';
type Row = [en: string, zhTW: string, zhCN: string, vi: string];

// 긴 것부터 (Korean Medicine Clinic이 Clinic으로 잘리지 않게)
const INSTITUTIONS: Row[] = [
  ['University Hospital', '大學醫院', '大学医院', 'Bệnh viện Đại học'],
  ['Long-term Care Hospital', '療養醫院', '疗养医院', 'Bệnh viện Dưỡng lão'],
  ['Korean Medicine Hospital', '韓醫醫院', '韩医医院', 'Bệnh viện Y học Hàn Quốc'],
  ["Children's Hospital", '兒童醫院', '儿童医院', 'Bệnh viện Nhi'],
  ['Korean Medicine Clinic', '韓醫診所', '韩医诊所', 'Phòng khám Y học Hàn Quốc'],
  ['Medical Center', '醫療院', '医疗院', 'Trung tâm Y tế'],
  ['Public Health Branch', '保健支所', '保健支所', 'Trạm Y tế'],
  ['Public Health Center', '保健所', '保健所', 'Trung tâm Y tế Công cộng'],
  ['Hospital', '醫院', '医院', 'Bệnh viện'],
  ['Clinic', '診所', '诊所', 'Phòng khám'],
];
const DEPARTMENTS: Row[] = [
  ['Rehabilitation Medicine', '復健科', '康复医学科', 'Phục hồi chức năng'],
  ['Internal Medicine', '內科', '内科', 'Nội khoa'],
  ['Thoracic Surgery', '胸腔外科', '胸外科', 'Ngoại Lồng ngực'],
  ['Plastic Surgery', '整形外科', '整形外科', 'Thẩm mỹ'],
  ['Family Medicine', '家庭醫學科', '家庭医学科', 'Y học Gia đình'],
  ['Pain Medicine', '疼痛科', '疼痛科', 'Giảm đau'],
  ['Neurosurgery', '神經外科', '神经外科', 'Ngoại Thần kinh'],
  ['Orthopedics', '骨科', '骨科', 'Chấn thương Chỉnh hình'],
  ['Dermatology', '皮膚科', '皮肤科', 'Da liễu'],
  ['Psychiatry', '身心科', '精神科', 'Tâm thần'],
  ['Pediatrics', '小兒科', '儿科', 'Nhi'],
  ['Radiology', '放射科', '放射科', 'Chẩn đoán Hình ảnh'],
  ['Neurology', '神經科', '神经科', 'Thần kinh'],
  ['Urology', '泌尿科', '泌尿外科', 'Tiết niệu'],
  ['OB/GYN', '婦產科', '妇产科', 'Sản Phụ khoa'],
  ['Surgery', '外科', '外科', 'Ngoại khoa'],
  ['ENT', '耳鼻喉科', '耳鼻喉科', 'Tai Mũi Họng'],
  ['Eye', '眼科', '眼科', 'Mắt'],
];
const COL: Record<Lang, 1 | 2 | 3> = { 'zh-TW': 1, 'zh-CN': 2, vi: 3 };
const isLocal = (lang: string): lang is Lang => lang in COL;

/** 영어 이름 → 중국어·베트남어 이름. 형식을 모르면 영어 이름 그대로 */
export function localHospitalName(nameEn: string, lang: string): string {
  if (!isLocal(lang)) return nameEn;
  // 시연 데이터의 끝 글자 구분자 ("Demo Dermatology Clinic A")
  const tail = nameEn.match(/ ([A-Z])$/)?.[1] ?? '';
  let rest = tail ? nameEn.slice(0, -2) : nameEn;
  const cut = (table: Row[]) => {
    const hit = table.find(([en]) => rest === en || rest.endsWith(` ${en}`));
    if (!hit) return undefined;
    rest = rest.slice(0, -hit[0].length).trim();
    return hit[COL[lang]];
  };
  const inst = cut(INSTITUTIONS);
  if (!inst) return nameEn;
  const dept = cut(DEPARTMENTS);
  const name = [rest, tail].filter(Boolean).join(' ');
  if (lang === 'vi') return [inst, dept, name].filter(Boolean).join(' ');
  return [name, `${dept ?? ''}${inst}`].filter(Boolean).join(' ');
}

// ---- 주소 로마자 표기 (scripts/romanize.mjs와 같은 자모 표)
const INITIAL = ['g', 'kk', 'n', 'd', 'tt', 'r', 'm', 'b', 'pp', 's', 'ss', '', 'j', 'jj', 'ch', 'k', 't', 'p', 'h'];
const VOWEL = ['a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 'wae', 'oe', 'yo', 'u', 'wo', 'we', 'wi', 'yu', 'eu', 'ui', 'i'];
const FINAL = ['', 'k', 'k', 'k', 'n', 'n', 'n', 't', 'l', 'k', 'm', 'l', 'l', 'l', 'p', 'l', 'm', 'p', 'p', 't', 't', 'ng', 't', 't', 'k', 't', 'p', 't'];
const syllable = (ch: string) => {
  const c = ch.codePointAt(0)! - 0xac00;
  return INITIAL[Math.floor(c / 588)] + VOWEL[Math.floor((c % 588) / 28)] + FINAL[c % 28];
};
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const compact = (ko: string) => cap([...ko].map(syllable).join(''));

// 주소 끝말 (긴 것부터)
const SUFFIX: [string, string][] = [
  ['대로', 'daero'], ['번길', 'beon-gil'], ['로', 'ro'], ['길', 'gil'], ['동', 'dong'], ['가', 'ga'],
  ['읍', 'eup'], ['면', 'myeon'], ['리', 'ri'], ['구', 'gu'], ['군', 'gun'],
];

/** 한글 낱말 하나 → 로마자 (예: 침산로 → Chimsan-ro, 동대구로12길 → Dongdaegu-ro 12-gil, 3층 → 3F) */
function romanWord(word: string): string {
  const w = word.replace(/지하([\d,]+)층/g, 'B$1F').replace(/([\d,]+)층/g, '$1F');
  const out: string[] = [];
  for (const run of w.match(/[가-힣]+|[^가-힣]+/g) ?? []) {
    if (!/[가-힣]/.test(run)) {
      out.push(run);
      continue;
    }
    const hit = SUFFIX.find(([ko]) => run.endsWith(ko));
    const stem = hit ? run.slice(0, -hit[0].length) : run;
    if (hit && !stem && out.length && /\d$/.test(out[out.length - 1])) {
      out[out.length - 1] += `-${hit[1]}`; // 12 + 길 → 12-gil
    } else if (hit && stem) {
      out.push(`${compact(stem)}-${hit[1]}`);
    } else {
      out.push(compact(run));
    }
  }
  return out.join(' ').replace(/\s+/g, ' ').replace(/ ([,)])/g, '$1').replace(/\( /g, '(');
}
const romanText = (ko: string) => ko.split(/\s+/).filter(Boolean).map(romanWord).join(' ');

const DISTRICT_ZH: Record<string, [string, string]> = {
  중구: ['中區', '中区'], 동구: ['東區', '东区'], 서구: ['西區', '西区'], 남구: ['南區', '南区'], 북구: ['北區', '北区'],
  수성구: ['壽城區', '寿城区'], 달서구: ['達西區', '达西区'], 달성군: ['達城郡', '达城郡'], 군위군: ['軍威郡', '军威郡'],
};

/** 한국어 도로명 주소 → 화면 언어 주소. 한국어 화면이거나 형식을 모르면 원문 그대로 */
export function localAddress(addr: string, lang: string): string {
  if (lang === 'ko') return addr;
  const m = addr.match(/^대구광역시\s+(\S+[구군])\s+(.+)$/);
  if (!m) return romanText(addr);
  const [, district] = m;
  // 원본 데이터에 주소가 두 번 들어간 행이 있다 ("경안로 848, 대구광역시 동구 경안로 848, 3층") → 두 번째는 뺀다
  const rest = m[2].replace(/,\s*대구광역시\s+\S+[구군]\s+[^,(]+/, '');
  const paren = rest.match(/\s*(\(.*\))\s*$/)?.[1] ?? '';
  const main = (paren ? rest.slice(0, rest.length - rest.match(/\s*\(.*\)\s*$/)![0].length) : rest).replace(/,\s*$/, '');
  const mainRo = romanText(main);
  const parenRo = paren ? ` ${romanText(paren)}` : '';
  if (lang === 'zh-TW' || lang === 'zh-CN') {
    const zh = DISTRICT_ZH[district]?.[lang === 'zh-TW' ? 0 : 1] ?? romanWord(district);
    return `${lang === 'zh-TW' ? '大邱廣域市' : '大邱广域市'} ${zh} ${mainRo}${parenRo}`;
  }
  // 영어·베트남어: 번지를 도로 이름 앞으로 (138 Chimsan-ro), 그다음 읍·면, 구·시 (영문 주소 순서)
  const town = mainRo.match(/^(\S+-(?:eup|myeon)) /)?.[1];
  const road = town ? mainRo.slice(town.length + 1) : mainRo;
  const swapped = road.replace(/^(\S+-(?:daero|ro|gil|beon-gil)(?: \S+-(?:gil|beon-gil))?) (\d[\d-]*)/, '$2 $1');
  return [swapped, town, romanWord(district), 'Daegu'].filter(Boolean).join(', ') + parenRo;
}
