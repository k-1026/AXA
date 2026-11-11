import type { DepartmentKey } from '../hospital/types';

// 예시 데이터는 한국어·영어를 함께 갖고, 사용자가 실제로 주고받은 대화는 입력한 언어 그대로 저장
export type ChatText = string | { ko: string; en: string };

export type Topic = 'hospital' | 'price' | 'interpret' | 'tour';

// 답변 아래 버튼을 눌렀을 때 할 일
export type ChipAction =
  | { kind: 'topic'; topic: Topic }
  | { kind: 'dept'; dept: DepartmentKey }
  | { kind: 'region'; district: string | null }
  | { kind: 'link'; to: string };

export interface Chip {
  label: ChatText;
  action: ChipAction;
}

export interface ChatMessage {
  id: string;
  role: 'bot' | 'user';
  text: ChatText;
  at: string; // ISO 시각
  chips?: Chip[];
}

export interface Conversation {
  id: string;
  createdAt: string; // ISO 시각. 목록 제목은 한국 시간 기준 YYYY.MM.DD
  topic?: Topic; // 목록 보조 정보의 "대화 요약"
  dept?: DepartmentKey; // 병원 찾기 중 고른 진료과
  messages: ChatMessage[];
  sample?: boolean; // 예시 데이터 (실제 상담 기록 아님)
}
