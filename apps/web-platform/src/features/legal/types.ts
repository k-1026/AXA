// 약관·정책 문서 형식. en이 없으면 한국어 원문만 있는 문서
export interface Text {
  ko: string;
  en?: string;
}

export interface LegalSection {
  heading?: Text;
  subheading?: Text; // 장 안의 작은 제목
  body?: Text[]; // 문단
  list?: { ordered?: boolean; items: Text[] };
  table?: { head: Text[]; rows: Text[][] };
  links?: { label: Text; url: string }[]; // '/'로 시작하면 사이트 안 링크
}

export interface LegalDocument {
  slug: 'privacy' | 'terms' | 'ai' | 'medical-law';
  title: Text;
  linkLabel?: Text; // 링크 목록에 쓸 짧은 이름 (없으면 title)
  updated: string; // YYYY-MM-DD
  sections: LegalSection[];
}
