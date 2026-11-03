import type { DepartmentKey } from '../hospital/types';

// 출처: 팀 문서 "병원별 시술 모음.docx" (진료과별 대표 진료·시술 분류, 자료 확인 2026-11-02)

// 가격은 범위만 표시. 근거 없는 숫자를 넣지 않도록 출처·기준일을 함께 적는다
export interface PriceRange {
  min: number;
  max: number;
  source: string;
  date: string;
}

export interface Procedure {
  ko: string;
  en: string;
  image?: string; // public/procedures/ 파일 이름. 없으면 빈 자리
  price?: PriceRange; // 없으면 "가격 확인 중"
}

export interface ProcedureCategory {
  dept: DepartmentKey;
  ko: string;
  en: string;
  items: Procedure[];
}

const list = (...rows: [string, string, string?][]): Procedure[] =>
  rows.map(([ko, en, image]) => ({ ko, en, image }));

export const PROCEDURE_CATEGORIES: ProcedureCategory[] = [
  // 피부과
  {
    dept: 'dermatology',
    ko: '주사·쁘띠 시술',
    en: 'Injectables',
    items: list(['보톡스', 'Botox', '01_botox'], ['필러', 'Filler', '02_dermal_fillers'], ['윤곽주사', 'Contouring Injection', '03_facial_contouring_injections']),
  },
  {
    dept: 'dermatology',
    ko: '색소·홍조',
    en: 'Pigmentation & Redness',
    items: list(
      ['기미·잡티·색소침착 치료', 'Melasma, Spot & Pigmentation Treatment', '04_pigmentation_treatment'],
      ['홍조·혈관 레이저', 'Redness & Vascular Laser', '05_redness_vascular_laser'],
    ),
  },
  {
    dept: 'dermatology',
    ko: '여드름·모공·흉터',
    en: 'Acne, Pores & Scars',
    items: list(['여드름 진료', 'Acne Care', '06_acne_care'], ['모공·여드름 흉터 레이저', 'Pore & Acne Scar Laser', '07_pore_acne_scar_laser']),
  },
  {
    dept: 'dermatology',
    ko: '탄력·비수술 리프팅',
    en: 'Firming & Non-surgical Lifting',
    items: list(
      ['초음파·고주파 리프팅', 'Ultrasound & Radiofrequency Lifting', '08_ultrasound_rf_lifting'],
      ['피부 탄력 관리', 'Skin Firming Care', '09_skin_firming'],
    ),
  },
  {
    dept: 'dermatology',
    ko: '피부관리·스킨부스터',
    en: 'Skin Care & Skin Boosters',
    items: list(['피부관리', 'Skin Care', '10_skin_care'], ['스킨부스터', 'Skin Booster', '11_skin_boosters']),
  },
  {
    dept: 'dermatology',
    ko: '점·양성 피부병변',
    en: 'Moles & Benign Skin Lesions',
    items: list(['점 제거', 'Mole Removal', '12_mole_removal'], ['양성 피부병변 진료', 'Benign Skin Lesion Care']),
  },
  {
    dept: 'dermatology',
    ko: '제모',
    en: 'Hair Removal',
    items: list(['여성·남성 레이저 제모', "Women's & Men's Laser Hair Removal", '14_laser_hair_removal']),
  },
  {
    dept: 'dermatology',
    ko: '바디·체형관리',
    en: 'Body Contouring Care',
    items: list(['바디주사', 'Body Injection', '15_body_contouring_injections'], ['비수술 체형관리', 'Non-surgical Body Contouring', '16_non_surgical_body_contouring']),
  },
  // 성형외과
  {
    dept: 'plastic',
    ko: '눈 성형',
    en: 'Eye Surgery',
    items: list(
      ['쌍꺼풀 수술', 'Double Eyelid Surgery', '17_double_eyelid_surgery'],
      ['눈매교정', 'Ptosis Correction', '18_ptosis_correction'],
      ['눈밑지방 재배치', 'Under-eye Fat Repositioning', '19_under_eye_fat_repositioning'],
    ),
  },
  {
    dept: 'plastic',
    ko: '코 성형',
    en: 'Nose Surgery',
    items: list(['융비술', 'Augmentation Rhinoplasty', '20_nasal_bridge_augmentation'], ['코끝 성형', 'Nasal Tip Plasty', '21_nose_tip_reshaping'], ['코 재수술', 'Revision Rhinoplasty', '22_revision_rhinoplasty']),
  },
  {
    dept: 'plastic',
    ko: '안면윤곽',
    en: 'Facial Contouring',
    items: list(['광대·턱 윤곽 성형', 'Cheekbone & Jaw Contouring', '23_cheekbone_jaw_contouring']),
  },
  {
    dept: 'plastic',
    ko: '거상·실리프팅',
    en: 'Lifts & Thread Lifting',
    items: list(['안면거상', 'Facelift', '24_facelift'], ['이마거상', 'Forehead Lift', '25_forehead_lift'], ['실리프팅', 'Thread Lift', '26_thread_lift']),
  },
  {
    dept: 'plastic',
    ko: '가슴 성형',
    en: 'Breast Surgery',
    items: list(['유방확대·축소·거상', 'Breast Augmentation, Reduction & Lift', '27_breast_reshaping']),
  },
  {
    dept: 'plastic',
    ko: '지방·체형 성형',
    en: 'Fat & Body Surgery',
    items: list(['지방흡입', 'Liposuction', '28_liposuction'], ['지방이식', 'Fat Grafting', '29_fat_grafting'], ['복부성형', 'Abdominoplasty', '30_tummy_tuck']),
  },
  {
    dept: 'plastic',
    ko: '바디필러',
    en: 'Body Filler',
    items: list(['바디필러 상담', 'Body Filler Consultation', '31_body_filler_consultation']),
  },
  {
    dept: 'plastic',
    ko: '흉터·재건',
    en: 'Scars & Reconstruction',
    items: list(
      ['흉터 성형', 'Scar Revision', '32_scar_revision'],
      ['외상·화상 후 재건', 'Reconstruction after Trauma & Burns', '33_trauma_burn_reconstruction'],
      ['유방재건', 'Breast Reconstruction'],
    ),
  },
  // 내과
  {
    dept: 'internal',
    ko: '건강검진',
    en: 'Health Checkups',
    items: list(
      ['기본·종합 건강검진', 'Basic & Comprehensive Health Checkup'],
      ['혈액·소변검사', 'Blood & Urine Tests'],
      ['결과 상담', 'Results Consultation'],
    ),
  },
  {
    dept: 'internal',
    ko: '소화기·내시경',
    en: 'Digestive & Endoscopy',
    items: list(
      ['위염·역류성 식도염·장질환 진료', 'Gastritis, Reflux Esophagitis & Bowel Disease Care'],
      ['위·대장내시경', 'Gastroscopy & Colonoscopy'],
    ),
  },
  {
    dept: 'internal',
    ko: '간·담도·췌장',
    en: 'Liver, Biliary & Pancreas',
    items: list(
      ['지방간·간염 진료', 'Fatty Liver & Hepatitis Care'],
      ['간기능검사', 'Liver Function Test'],
      ['복부초음파', 'Abdominal Ultrasound'],
    ),
  },
  {
    dept: 'internal',
    ko: '심혈관·만성질환',
    en: 'Cardiovascular & Chronic Disease',
    items: list(['고혈압·이상지질혈증·부정맥 진료', 'Hypertension, Dyslipidemia & Arrhythmia Care']),
  },
  {
    dept: 'internal',
    ko: '내분비·대사',
    en: 'Endocrine & Metabolism',
    items: list(['당뇨병·갑상선질환·비만·골다공증 진료', 'Diabetes, Thyroid, Obesity & Osteoporosis Care']),
  },
  {
    dept: 'internal',
    ko: '호흡기·알레르기',
    en: 'Respiratory & Allergy',
    items: list(['기침·천식·폐질환·알레르기 진료', 'Cough, Asthma, Lung Disease & Allergy Care']),
  },
  {
    dept: 'internal',
    ko: '신장',
    en: 'Kidney',
    items: list(['신장기능 이상·단백뇨 진료', 'Kidney Dysfunction & Proteinuria Care']),
  },
  {
    dept: 'internal',
    ko: '예방접종',
    en: 'Vaccination',
    items: list(['독감·간염·HPV 백신 접종 상담', 'Flu, Hepatitis & HPV Vaccination Consultation']),
  },
  {
    dept: 'internal',
    ko: '영양·수액',
    en: 'Nutrition & IV Therapy',
    items: list(
      ['영양상태 평가', 'Nutritional Assessment'],
      ['필요에 따른 영양·수액 치료', 'Nutrition & IV Therapy as Needed'],
    ),
  },
  // 안과
  {
    dept: 'ophthalmology',
    ko: '시력교정',
    en: 'Vision Correction',
    items: list(['라식', 'LASIK'], ['라섹', 'LASEK'], ['스마일', 'SMILE'], ['안내렌즈삽입술', 'Implantable Contact Lens (ICL)']),
  },
  {
    dept: 'ophthalmology',
    ko: '노안·백내장',
    en: 'Presbyopia & Cataract',
    items: list(
      ['노안 검사·교정 상담', 'Presbyopia Exam & Correction Consultation'],
      ['백내장 수술·인공수정체 상담', 'Cataract Surgery & Intraocular Lens Consultation'],
    ),
  },
  {
    dept: 'ophthalmology',
    ko: '안구건조·안구표면',
    en: 'Dry Eye & Ocular Surface',
    items: list(['안구건조증', 'Dry Eye'], ['결막염', 'Conjunctivitis'], ['눈꺼풀염 진료', 'Blepharitis Care']),
  },
  {
    dept: 'ophthalmology',
    ko: '녹내장',
    en: 'Glaucoma',
    items: list(
      ['안압·시신경·시야 검사', 'Eye Pressure, Optic Nerve & Visual Field Tests'],
      ['약물·레이저·수술 치료', 'Medication, Laser & Surgical Treatment'],
    ),
  },
  {
    dept: 'ophthalmology',
    ko: '망막·황반',
    en: 'Retina & Macula',
    items: list([
      '황반변성·당뇨망막병증·망막열공·망막박리 진료',
      'Macular Degeneration, Diabetic Retinopathy, Retinal Tear & Detachment Care',
    ]),
  },
  {
    dept: 'ophthalmology',
    ko: '각막',
    en: 'Cornea',
    items: list(
      ['각막염·원추각막 진료', 'Keratitis & Keratoconus Care'],
      ['각막이식 상담', 'Corneal Transplant Consultation'],
    ),
  },
  {
    dept: 'ophthalmology',
    ko: '사시·소아안과',
    en: 'Strabismus & Pediatric Eye Care',
    items: list(
      ['사시·약시 진료', 'Strabismus & Amblyopia Care'],
      ['소아 시력·굴절검사', 'Pediatric Vision & Refraction Tests'],
    ),
  },
  {
    dept: 'ophthalmology',
    ko: '눈꺼풀·눈물길',
    en: 'Eyelid & Tear Duct',
    items: list(['안검하수·눈꺼풀 이상·눈물길 질환 진료', 'Ptosis, Eyelid & Tear Duct Disorder Care']),
  },
];
