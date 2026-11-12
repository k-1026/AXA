import { Fragment, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { LANGUAGES } from '../../i18n';
import type { DepartmentKey } from '../hospital/types';
import type { ChatCard, HospitalBrief } from './chatApi';

// 카드의 진료과는 한국어 이름(피부과 등)으로 온다 (ai/agent/tools/chat_tools.py DEPT_CODES와 같은 표)
// 화면 진료과 키가 있는 것만 번역하고, 나머지(치과·한방 등)는 받은 그대로 보여 준다
const DEPT_KEYS: Record<string, DepartmentKey> = { 피부과: 'dermatology', 성형외과: 'plastic', 내과: 'internal', 안과: 'ophthalmology' };
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
      <strong>{i18n.language === 'ko' ? h.name_ko : h.name_en}</strong>
      <span>
        {t(`district.${h.district}`, { defaultValue: h.district })} · {h.departments.map((d) => deptLabel(t, d)).join(', ')}
      </span>
      <span className="chat-card-badges">
        {h.is_registered_facility && <em>{t('chat.card.registered')}</em>}
        {h.staff_languages.length > 0 && <em>{t('chat.card.staffLangs', { langs: h.staff_languages.map((l) => langLabel(l, i18n.language)).join(', ') })}</em>}
        {h.ai_translation_chat && <em>{t('chat.card.aiTranslation')}</em>}
      </span>
      {reasons && reasons.length > 0 && <span className="chat-card-reasons">{reasons.join(' · ')}</span>}
    </li>
  );
}

function Card({ card }: { card: ChatCard }) {
  const { t, i18n } = useTranslation();
  switch (card.type) {
    case 'hospital_list':
      return (
        <section className="chat-card">
          <h3>{t('chat.card.hospitalList', { count: card.data.count })}</h3>
          <ul>
            {card.data.hospitals.map((h) => (
              <HospitalRow key={h.hospital_id} h={h} />
            ))}
          </ul>
          <p className="chat-card-note">{card.data.note}</p>
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
          <p className="chat-card-note">{card.data.basis}</p>
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
          <p className="chat-card-note">{card.data.note}</p>
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
          <fieldset>
            <legend>{t('chat.card.consents')}</legend>
            {card.data.consents_required.map((k) => (
              <label key={k}>
                <input type="checkbox" disabled /> {t(`chat.consent.${k}`, { defaultValue: k })}
              </label>
            ))}
          </fieldset>
          {/* 제출 = 사람이 쓰는 요청서와 같은 API. 예약 요청 API(B)가 생기면 연결 */}
          <button type="button" disabled>
            {t('chat.card.submit')}
          </button>
          <p className="chat-card-note">{t('chat.card.submitLater')}</p>
        </section>
      );
    }
    default:
      return null; // 나머지 카드(출처·시간 후보·내 요청·사후 문의)는 다음 단계에서
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
