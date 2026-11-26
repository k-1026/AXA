import { Fragment, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { LANGUAGES } from '../../i18n';
import type { DepartmentKey } from '../hospital/types';
import type { ChatCard, HospitalBrief } from './chatApi';
import { localHospitalName } from '../hospital/localize';
import { BookingDraftActions, QuestionCard } from './ActionCards';

// 카드의 진료과는 한국어 이름(피부과 등)으로 온다 (ai/agent/tools/chat_tools.py DEPT_CODES와 같은 표)
// 화면 진료과 키가 있는 것만 번역하고, 나머지(치과·한방 등)는 받은 그대로 보여 준다
const DEPT_KEYS: Record<string, DepartmentKey> = { 피부과: 'dermatology', 성형외과: 'plastic', 내과: 'internal', 안과: 'ophthalmology', 한방: 'korean_medicine', 한의원: 'korean_medicine' };
const deptLabel = (t: TFunction, d: string) => {
  const key = DEPT_KEYS[d] ?? (Object.values(DEPT_KEYS).includes(d as DepartmentKey) ? d : null);
  return key ? t(`dept.${key}`) : d;
};

// 직원 응대 언어 코드(en·zh·vi 등) → 화면 언어로 된 이름. 사이트 언어 목록에 있으면 그 이름, 없으면 브라우저의 언어 이름
function langLabel(code: string, uiLang: string) {
  const own = LANGUAGES.find((l) => l.code === code)?.label;
  if (own) return own;
  try {
    return new Intl.DisplayNames([uiLang], { type: 'language' }).of(code) ?? code;
  } catch {
    return code;
  }
}

// 요일 코드(mon~sun) → 화면 언어의 요일 이름 (2024-01-01이 월요일)
const WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
function weekdayLabel(code: string, uiLang: string) {
  const i = WEEKDAYS.indexOf(code);
  return i < 0 ? code : new Intl.DateTimeFormat(uiLang, { weekday: 'long', timeZone: 'UTC' }).format(Date.UTC(2024, 0, 1 + i));
}

// 추천 카드의 "맞는 이유"는 백엔드가 영어 고정 형식으로 보낸다 (ai/agent/tools/chat_tools.py recommend_hospitals).
// 아는 형식은 화면 언어로 바꾸고, 모르는 형식(백엔드가 바뀐 경우)은 받은 그대로 보여 준다
function reasonLabel(t: TFunction, uiLang: string, s: string): string {
  let m: RegExpMatchArray | null;
  if ((m = s.match(/^staff speak (\S+)$/))) return t('chat.card.reasons.staffLang', { lang: langLabel(m[1], uiLang) });
  if (s === 'AI translation chat available') return t('chat.card.reasons.aiTranslation');
  if ((m = s.match(/^open on (\w+) \((.+)\)$/))) return t('chat.card.reasons.openOn', { day: weekdayLabel(m[1], uiLang), hours: m[2] });
  if ((m = s.match(/^consultation slots on (\S+)$/))) return t('chat.card.reasons.slotsOn', { date: m[1] });
  if ((m = s.match(/^in (.+)$/))) return t('chat.card.reasons.inDistrict', { district: t(`district.${m[1]}`, { defaultValue: m[1] }) });
  return s;
}

// AI 답 문장: 줄바꿈과 **굵게**만 살린다 (HTML로 넣지 않음 → 답에 섞인 태그가 실행되지 않음)
export function AnswerText({ text }: { text: string }) {
  const bold = (line: string): ReactNode[] =>
    line.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
    );
  return (
    <div className="chat-answer">
      {text.split('\n').map((line, i) => (line.trim() ? <p key={i}>{bold(line)}</p> : null))}
    </div>
  );
}

function HospitalRow({ h, reasons }: { h: HospitalBrief; reasons?: string[] }) {
  const { t, i18n } = useTranslation();
  return (
    <li className="chat-card-hospital">
      <strong>{i18n.language === 'ko' ? h.name_ko : localHospitalName(h.name_en, i18n.language)}</strong>
      <span>
        {t(`district.${h.district}`, { defaultValue: h.district })} · {h.departments.map((d) => deptLabel(t, d)).join(', ')}
      </span>
      <span className="chat-card-badges">
        {h.is_registered_facility && <em>{t('chat.card.registered')}</em>}
        {h.staff_languages.length > 0 && <em>{t('chat.card.staffLangs', { langs: h.staff_languages.map((l) => langLabel(l, i18n.language)).join(', ') })}</em>}
        {h.ai_translation_chat && <em>{t('chat.card.aiTranslation')}</em>}
      </span>
      {reasons && reasons.length > 0 && (
        <span className="chat-card-reasons">{reasons.map((r) => reasonLabel(t, i18n.language, r)).join(' · ')}</span>
      )}
    </li>
  );
}

// 사후관리 화면으로 넘길 값 (주소에 글을 넣지 않고 화면 이동 state로 — 기록·공유 주소에 남지 않게)
export interface AftercareHandoff {
  booking?: string | null;
  draft?: string;
}

function AftercareCard({ data }: { data: Extract<ChatCard, { type: 'aftercare_thread' }>['data'] }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const state: AftercareHandoff = { booking: data.booking_id, draft: data.first_message };
  return (
    <section className="chat-card">
      <h3>{t('chat.card.aftercare')}</h3>
      <blockquote className="chat-card-quote">{data.first_message}</blockquote>
      <button type="button" onClick={() => navigate('/aftercare', { state })}>
        {t('chat.card.aftercareOpen')}
      </button>
      <p className="chat-card-note">{t('chat.card.aftercareNote')}</p>
    </section>
  );
}

/** 가격 가이드 화면으로 가는 버튼 — 챗봇은 숫자를 말하지 않고, 공공 비급여 범위는 가격 가이드에서 본다 */
function PriceGuideCard({ q, dept }: { q?: string; dept?: DepartmentKey }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = new URLSearchParams();
  if (dept) params.set('dept', dept);
  if (q) params.set('q', q);
  const qs = params.toString();
  return (
    <section className="chat-card">
      {(q || dept) && <h3>{q ? `"${q}"` : t(`dept.${dept}`)}</h3>}
      <button type="button" onClick={() => navigate(`/prices${qs ? `?${qs}` : ''}`)}>
        {t('chat.link.prices')}
      </button>
      {/* 금액 고지(공공 비급여·내국인 기준·병원 확인)는 가격 가이드 화면에 있다 */}
    </section>
  );
}

function Card({ card }: { card: ChatCard }) {
  const { t, i18n } = useTranslation();
  switch (card.type) {
    case 'hospital_list':
      return (
        <section className="chat-card">
          {/* 제목 숫자 = 카드에 보이는 병원 수 (검색 전체 수 count와 다를 수 있음 — 답 문장과 어긋나 보이던 것, 2026-11-26) */}
          <h3>{t('chat.card.hospitalList', { count: card.data.hospitals.length })}</h3>
          <ul>
            {card.data.hospitals.map((h) => (
              <HospitalRow key={h.hospital_id} h={h} />
            ))}
          </ul>
          {/* 카드 안내는 카드 종류마다 정해진 문구라 화면 언어로 보여 준다 (백엔드 note는 AI 모델이 읽는 영어 원문) */}
          <p className="chat-card-note">{t('chat.card.listNote')}</p>
        </section>
      );
    case 'hospital_suggestions':
      return (
        <section className="chat-card">
          <h3>{t('chat.card.suggestions', { count: card.data.count })}</h3>
          <ul>
            {card.data.suggestions.map((h) => (
              <HospitalRow key={h.hospital_id} h={h} reasons={h.match_reasons} />
            ))}
          </ul>
          <p className="chat-card-note">{t('chat.card.suggestBasis')}</p>
        </section>
      );
    case 'hospital_detail':
      return (
        <section className="chat-card">
          <ul>
            <HospitalRow h={card.data} />
          </ul>
          <p className="chat-card-note">
            {card.data.address_en} · {card.data.tel}
          </p>
        </section>
      );
    case 'price_guide':
      return <PriceGuideCard q={card.data.q} dept={card.data.dept} />;
    case 'price_list':
      return (
        <section className="chat-card">
          <h3>{t('chat.card.prices')}</h3>
          <ul>
            {card.data.prices.map((p, i) => (
              <li key={i}>
                {p.item_en}: {p.min.toLocaleString(i18n.language)}–{p.max.toLocaleString(i18n.language)} {p.currency}
              </li>
            ))}
          </ul>
          <p className="chat-card-note">{t('chat.card.priceNote')}</p>
        </section>
      );
    case 'booking_draft': {
      const d = card.data.draft as Record<string, unknown>;
      const slots = (d.preferred_slots as string[] | undefined) ?? [];
      return (
        <section className="chat-card is-draft">
          <h3>{t('chat.card.draft')}</h3>
          <dl>
            <dt>{t('chat.card.hospital')}</dt>
            <dd>{String(d.hospital_name_en ?? card.data.hospital_id)}</dd>
            <dt>{t('chat.card.department')}</dt>
            <dd>{typeof d.department === 'string' ? deptLabel(t, d.department) : '-'}</dd>
            <dt>{t('chat.card.slots')}</dt>
            <dd>{slots.join(', ') || '-'}</dd>
          </dl>
          {/* 제출 = 사람이 쓰는 요청서와 같은 API (결정 3). 동의를 체크하고 환자가 누름 */}
          <BookingDraftActions data={card.data} />
        </section>
      );
    }
    case 'aftercare_thread':
      return <AftercareCard data={card.data} />;
    case 'hospital_question':
      return <QuestionCard data={card.data} />;
    default:
      return null; // 나머지 카드(출처·시간 후보·내 요청)는 다음 단계에서
  }
}

export function ChatCards({ cards }: { cards: ChatCard[] }) {
  if (!cards.length) return null;
  return (
    <div className="chat-cards">
      {cards.map((c, i) => (
        <Card key={i} card={c} />
      ))}
    </div>
  );
}
