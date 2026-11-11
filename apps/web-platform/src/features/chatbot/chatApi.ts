// 챗봇 API (7d, docs/plan-step7-chat-api.md). 로그인한 회원만 — 토큰이 없으면 부르지 않는다
// 카드 형식의 기준은 백엔드 ai/agent/schemas.py (OpenAPI → packages/shared-types가 생기면 그 타입으로 교체)
import { api } from '../../components/api';

export type ChatLang = 'ko' | 'en' | 'zh-TW' | 'zh-CN' | 'vi';

export interface HospitalBrief {
  hospital_id: number;
  name_ko: string;
  name_en: string;
  district: string;
  departments: string[];
  is_registered_facility: boolean;
  staff_languages: string[];
  ai_translation_chat: boolean;
}

export type ChatCard =
  | { type: 'hospital_list'; data: { count: number; hospitals: HospitalBrief[]; note: string } }
  | { type: 'hospital_suggestions'; data: { count: number; suggestions: (HospitalBrief & { match_reasons: string[] })[]; basis: string } }
  | {
      type: 'hospital_detail';
      data: HospitalBrief & { hours: Record<string, string | null>; address_en: string; tel: string; hours_source: string; can_request_consultation: boolean };
    }
  | { type: 'price_list'; data: { prices: { hospital_id: number; item: string; item_en: string; min: number; max: number; currency: string }[]; note: string } }
  | {
      type: 'booking_draft';
      data: {
        status: 'draft';
        hospital_id: number;
        draft: Record<string, unknown>;
        request: Record<string, unknown>;
        consents_required: string[];
        note: string;
      };
    }
  | { type: 'sources' | 'time_slots' | 'booking_list' | 'aftercare_thread'; data: Record<string, unknown> };

export interface ChatResponse {
  session_id: string;
  text: string;
  cards: ChatCard[];
  ai_generated: boolean;
  blocked: boolean;
  medical_notice: boolean;
}

const LANGS: ChatLang[] = ['ko', 'en', 'zh-TW', 'zh-CN', 'vi'];
export const chatLang = (lng: string): ChatLang => (LANGS as string[]).includes(lng) ? (lng as ChatLang) : 'en';

export const askChatbot = (token: string, sessionId: string | undefined, message: string, language: ChatLang) =>
  api<ChatResponse>('/chatbot/ask', { method: 'POST', token, body: { session_id: sessionId ?? null, message, language } });

export const deleteChatSession = (token: string, sessionId: string) =>
  api<void>(`/chatbot/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE', token });

// 7e: 지난 대화 (글만 — 카드는 서버에 저장하지 않음)
export interface ChatSessionOut {
  id: string;
  title: string;
  lang: string;
  created_at: string;
  last_message_at: string;
}

export interface ChatSessionDetail extends ChatSessionOut {
  messages: { role: 'user' | 'assistant'; content: string; refused: boolean; created_at: string }[];
}

export const listChatSessions = (token: string) => api<ChatSessionOut[]>('/chatbot/sessions', { token });

export const getChatSession = (token: string, sessionId: string) =>
  api<ChatSessionDetail>(`/chatbot/sessions/${encodeURIComponent(sessionId)}`, { token });
