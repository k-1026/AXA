import type { DepartmentKey } from '../hospital/types';
import type { ChatCard } from './chatApi';

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
  // 아래는 AI 답(회원)일 때만
  cards?: ChatCard[];
  ai?: boolean; // "AI 생성" 표시 (인공지능기본법 제31조). 응급 고정 문구는 false
  medicalNotice?: boolean; // "의료 상담이 아닙니다" 고지
  pending?: boolean; // 답을 기다리는 중
  failed?: boolean; // 서버 오류로 답을 못 받음
}

export interface Conversation {
  id: string;
  createdAt: string; // ISO 시각. 목록 제목은 한국 시간 기준 YYYY.MM.DD
  topic?: Topic; // 목록 보조 정보의 "대화 요약"
  dept?: DepartmentKey; // 병원 찾기 중 고른 진료과
  messages: ChatMessage[];
  sample?: boolean; // 예시 데이터 (실제 상담 기록 아님)
  serverId?: string; // 회원: 서버 대화 id (POST /chatbot/ask의 session_id)
}
