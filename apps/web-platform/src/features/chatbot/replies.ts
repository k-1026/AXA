// AI 연결 전 데모 답변. 정해진 안내만 하고 병원을 고르거나 추천하지 않는다 (docs/compliance.md)
// 응급 증상 단어가 보이면 다른 답보다 먼저 119 안내 (AI 서비스 안내 "응급 상황")
import type { TFunction } from 'i18next';
import { DEPARTMENTS } from '../hospital/filters';
import type { DepartmentKey } from '../hospital/types';
import type { Chip, ChipAction, Conversation, Topic } from './types';

export interface BotReply {
  text: string;
  chips?: Chip[];
  topic?: Topic;
  dept?: DepartmentKey;
}

const EMERGENCY = ['가슴 통증', '가슴이 아파', '숨이', '호흡', '출혈', '피가 많이', '의식', '쓰러', '119', 'chest pain', "can't breathe", 'bleeding', 'unconscious', 'emergency', '胸痛', '呼吸', '出血', 'khó thở', 'chảy máu'];

const DEPT_WORDS: Record<DepartmentKey, string[]> = {
  dermatology: ['피부', 'derma', 'skin', '皮肤', '皮膚', 'da liễu'],
  plastic: ['성형', 'plastic', '整形', 'thẩm mỹ'],
  internal: ['내과', 'internal', '内科', '內科', 'nội'],
  ophthalmology: ['안과', 'eye', 'ophthal', '眼科', 'mắt'],
};

const TOPIC_WORDS: Record<Topic, string[]> = {
  price: ['가격', '비용', '얼마', 'price', 'cost', '价格', '價格', '费用', 'giá', 'chi phí'],
  interpret: ['통역', '번역', 'interpret', 'translat', '翻译', '翻譯', 'phiên dịch'],
  tour: ['관광', '여행', '가볼', 'tour', 'travel', 'sightsee', '旅游', '旅遊', '观光', 'du lịch'],
  hospital: ['병원', '의원', 'hospital', 'clinic', '医院', '醫院', 'bệnh viện'],
};

const has = (text: string, words: string[]) => {
  const s = text.toLowerCase();
  return words.some((w) => s.includes(w.toLowerCase()));
};

export const topicChips = (t: TFunction): Chip[] =>
  (['hospital', 'price', 'interpret', 'tour'] as Topic[]).map((topic) => ({
    label: t(`chat.topic.${topic}`),
    action: { kind: 'topic', topic },
  }));

function askDept(t: TFunction): BotReply {
  return {
    text: t('chat.bot.askDept'),
    topic: 'hospital',
    chips: DEPARTMENTS.map((dept) => ({ label: t(`dept.${dept}`), action: { kind: 'dept', dept } })),
  };
}

function askRegion(t: TFunction, dept: DepartmentKey): BotReply {
  return {
    text: t('chat.bot.askRegion'),
    topic: 'hospital',
    dept,
    chips: [
      { label: t('chat.region.junggu'), action: { kind: 'region', district: '중구' } },
      { label: t('chat.region.suseong'), action: { kind: 'region', district: '수성구' } },
      { label: t('chat.region.any'), action: { kind: 'region', district: null } },
    ],
  };
}

function byTopic(t: TFunction, topic: Topic): BotReply {
  if (topic === 'hospital') return askDept(t);
  if (topic === 'price')
    return { text: t('chat.bot.price'), topic, chips: [{ label: t('chat.link.prices'), action: { kind: 'link', to: '/prices' } }] };
  return { text: t(`chat.bot.${topic}`), topic };
}

/** 버튼(chip)을 눌렀을 때 */
export function replyToChip(t: TFunction, action: ChipAction, conv: Conversation): BotReply | null {
  switch (action.kind) {
    case 'topic':
      return byTopic(t, action.topic);
    case 'dept':
      return askRegion(t, action.dept);
    case 'region': {
      const params = new URLSearchParams();
      if (conv.dept) params.set('dept', conv.dept);
      if (action.district) params.set('district', action.district);
      const q = params.toString();
      return {
        text: t('chat.bot.hospitals'),
        topic: 'hospital',
        chips: [{ label: t('chat.link.hospitals'), action: { kind: 'link', to: `/hospitals${q ? `?${q}` : ''}` } }],
      };
    }
    case 'link':
      return null; // 페이지 이동만
  }
}

/** 직접 입력했을 때 */
export function replyToText(t: TFunction, text: string): BotReply {
  if (has(text, EMERGENCY)) return { text: t('chat.bot.emergency') };
  const dept = DEPARTMENTS.find((d) => has(text, DEPT_WORDS[d]));
  if (dept) return askRegion(t, dept);
  for (const topic of ['price', 'interpret', 'tour', 'hospital'] as Topic[]) {
    if (has(text, TOPIC_WORDS[topic])) return byTopic(t, topic);
  }
  return { text: t('chat.bot.fallback'), chips: topicChips(t) };
}
