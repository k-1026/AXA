// 개인정보 처리방침·이용약관·AI 서비스 안내·의료 관련 법령 안내 (초안)
// 근거: docs/compliance.md. 법률 검토 전이므로 화면에 "초안" 표시를 함께 띄운다
// [미정] 항목은 운영 주체·연락처가 정해지면 채운다
import type { LegalDocument, Text } from './types';
import { PRIVACY } from './privacy';
import { TERMS } from './terms';
import { AI_NOTICE } from './aiNotice';

const L = (ko: string, en: string): Text => ({ ko, en });

const LAW = {
  medical: { label: L('의료법', 'Medical Service Act'), url: 'https://www.law.go.kr/법령/의료법' },
  foreignPatient: {
    label: L('의료 해외진출 및 외국인환자 유치 지원에 관한 법률', 'Act on Support for Overseas Expansion of Medical Services and Attraction of International Patients'),
    url: 'https://www.law.go.kr/법령/의료해외진출및외국인환자유치지원에관한법률',
  },
  privacy: { label: L('개인정보 보호법', 'Personal Information Protection Act'), url: 'https://www.law.go.kr/법령/개인정보보호법' },
};

export const LEGAL_DOCUMENTS: LegalDocument[] = [
  PRIVACY,
  TERMS,
  AI_NOTICE,
  {
    slug: 'medical-law',
    title: L('의료 관련 법령 안내', 'Medical Law Notice'),
    updated: '2026-11-03',
    sections: [
      {
        heading: L('1. 병원 소개와 수수료', '1. Introducing hospitals and fees'),
        body: [
          L(
            '한국 의료법은 영리 목적으로 환자를 병원에 소개·알선·유인하는 행위를 제한하고, 등록한 외국인환자 유치업자의 유치 행위는 예외로 둡니다 (의료법 제27조 제3항 제2호). MediDaegu는 등록 외국인환자 유치업자라는 가정으로 설계·시연하는 서비스이며, 입점 병원으로부터 건당 중개수수료를 받는 구조입니다. 수수료는 법령이 정한 상한 안에서만 받고, 이용자(환자)에게는 받지 않습니다.',
            'Korean medical law restricts introducing, brokering or inducing patients to hospitals for profit, with an exception for registered international patient facilitators (Medical Service Act, Article 27(3)(2)). MediDaegu is designed and demonstrated on the assumption that it is a registered facilitator, and its model is a per-case brokerage fee paid by partner hospitals. Fees stay within the legal cap, and patients are not charged.',
          ),
          L(
            '목록과 지도는 거리·가나다순으로만 정렬합니다. 챗봇은 입력한 조건(진료과·지역·언어 등)에 맞는 병원을 제안할 수 있지만, 의료 수준을 비교한 순위가 아닙니다. 병원 순위·"최고"·"최저가"·할인율·후기·전후 사진은 보여주지 않습니다.',
            'Lists and maps are sorted only by distance or alphabetical order. The chatbot may suggest hospitals that match the conditions you enter (department, area, language, etc.), but this is not a ranking of medical quality. We do not show rankings, "best" or "lowest price" labels, discount rates, reviews or before-and-after photos.',
          ),
          L(
            '챗봇은 병원에 보낼 상담 요청서 초안을 함께 만들 수 있습니다. 요청서는 이용자가 확인하고 직접 제출하며, 예약 확정은 병원이 합니다.',
            'The chatbot can help you prepare a draft consultation request. You review and submit it yourself, and the hospital confirms any booking.',
          ),
        ],
      },
      {
        heading: L('2. 의료 상담이 아닙니다', '2. Not medical advice'),
        body: [
          L(
            '챗봇과 화면의 정보는 증상 판단이나 시술 선택을 대신하지 않습니다 (의료법 제27조 제1항). 진료에 관한 질문은 병원에 직접 문의하세요.',
            'The chatbot and on-screen information do not replace a diagnosis or treatment decision (Medical Service Act, Article 27(1)). Please ask the hospital directly about medical questions.',
          ),
        ],
      },
      {
        heading: L('3. 외국인환자 유치', '3. International patient attraction'),
        body: [
          L(
            '외국인환자 유치는 등록한 의료기관과 유치업자만 할 수 있습니다. MediDaegu는 예약 요청 기능을 등록 유치의료기관에만 열고, 병원 상세에 등록 여부를 표시할 예정입니다.',
            'Only registered medical institutions and facilitators may attract international patients. MediDaegu will enable booking requests only for registered institutions and plans to show registration status on hospital pages.',
          ),
        ],
      },
      {
        heading: L('4. 건강정보 보호', '4. Health information'),
        body: [
          L(
            '건강정보는 민감정보라 별도 동의를 받은 경우에만 처리합니다 (개인정보 보호법 제23조). 자세한 내용은 개인정보 처리방침을 보세요.',
            'Health information is sensitive data and is processed only with separate consent (Personal Information Protection Act, Article 23). See the Privacy Policy for details.',
          ),
        ],
        links: [LAW.medical, LAW.foreignPatient, LAW.privacy],
      },
    ],
  },
];

// 한국어 외 언어는 영어로 표시 (병원 이름과 같은 규칙). 영어본이 없으면 한국어 원문
export const pickText = (x: Text, lang: string) => (lang !== 'ko' && x.en ? x.en : x.ko);

export const findLegalDocument =(slug: string | undefined) => LEGAL_DOCUMENTS.find((d) => d.slug === slug);
