// 챗봇 카드 중 환자가 직접 "보내는" 두 가지. AI는 초안만 만들고, 보내기는 항상 환자가 버튼으로 (결정 3·32)
// - 요청서 초안(booking_draft): 동의를 체크하고 [요청 보내기] → 사람이 쓰는 요청서와 같은 API
// - 방문 전 질문 초안(hospital_question): 글을 고치고 [보내기] → POST /me/booking-requests/{id}/questions
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../../components/api';
import { useAuth } from '../../components/auth';
import { bookingErrorKey } from '../consult/bookingErrors';
import { OVERSEAS_VERSION } from '../consult/bookingApi';
import { PRIVACY } from '../legal/privacy';
import type { ChatCard } from './chatApi';

type Draft = Extract<ChatCard, { type: 'booking_draft' }>['data'];
type Question = Extract<ChatCard, { type: 'hospital_question' }>['data'];

// 동의 문구 버전: privacy = 개인정보 처리방침 개정일, 건강정보·해외 AI 번역 = 안내 문구 날짜
const versionOf = (kind: string) => (kind === 'privacy' ? PRIVACY.updated : OVERSEAS_VERSION);

export function BookingDraftActions({ data }: { data: Draft }) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const [agreed, setAgreed] = useState<Record<string, boolean>>({});
  const [state, setState] = useState<'idle' | 'busy' | 'sent'>('idle');
  const [error, setError] = useState<string | null>(null);
  const ready = data.consents_required.every((k) => agreed[k]);

  const submit = async () => {
    if (!token || !ready) return;
    setState('busy');
    setError(null);
    try {
      await api(`/hospitals/${data.hospital_id}/booking-requests`, {
        method: 'POST',
        token,
        body: { ...data.request, consents: data.consents_required.map((kind) => ({ kind, version: versionOf(kind) })) },
      });
      setState('sent');
    } catch (e) {
      setError(bookingErrorKey(e));
      setState('idle');
    }
  };

  if (state === 'sent') {
    return (
      <p className="chat-card-done" role="status">
        {t('chat.card.submitted')} <Link to="/mypage/bookings">{t('chat.card.goBookings')}</Link>
      </p>
    );
  }
  return (
    <>
      <fieldset>
        <legend>{t('chat.card.consents')}</legend>
        {data.consents_required.map((k) => (
          <label key={k}>
            <input type="checkbox" checked={!!agreed[k]} onChange={(e) => setAgreed({ ...agreed, [k]: e.target.checked })} />{' '}
            {t(`chat.consent.${k}`, { defaultValue: k })}
          </label>
        ))}
      </fieldset>
      {error && (
        <p className="chat-card-error" role="alert">
          {t(error)}
        </p>
      )}
      <button type="button" onClick={submit} disabled={!token || !ready || state === 'busy'}>
        {t(state === 'busy' ? 'auth.submitting' : 'chat.card.submit')}
      </button>
      <p className="chat-card-note">{t('chat.card.submitNote')}</p>
    </>
  );
}

export function QuestionCard({ data }: { data: Question }) {
  const { t } = useTranslation();
  const { token } = useAuth();
  const [text, setText] = useState(data.draft);
  const [state, setState] = useState<'idle' | 'busy' | 'sent'>('idle');
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    if (!token || !text.trim()) return;
    setState('busy');
    setError(null);
    try {
      await api(`/me/booking-requests/${data.booking_id}/questions`, { method: 'POST', token, body: { text: text.trim() } });
      setState('sent');
    } catch (e) {
      setError(bookingErrorKey(e));
      setState('idle');
    }
  };

  return (
    <section className="chat-card is-draft">
      <h3>{t('chat.card.question', { hospital: data.hospital_name_en ?? '' })}</h3>
      {state === 'sent' ? (
        <>
          <blockquote className="chat-card-quote">{text.trim()}</blockquote>
          <p className="chat-card-done" role="status">
            {t('chat.card.questionSent')} <Link to="/booking">{t('chat.card.goConsult')}</Link>
          </p>
        </>
      ) : (
        <>
          <textarea
            className="chat-card-edit"
            rows={3}
            maxLength={1000}
            value={text}
            onChange={(e) => setText(e.target.value)}
            aria-label={t('chat.card.questionEdit')}
          />
          {error && (
            <p className="chat-card-error" role="alert">
              {t(error)}
            </p>
          )}
          <button type="button" onClick={send} disabled={!token || !text.trim() || state === 'busy'}>
            {t(state === 'busy' ? 'auth.submitting' : 'chat.card.questionSend')}
          </button>
          <p className="chat-card-note">{t('chat.card.questionNote')}</p>
        </>
      )}
    </section>
  );
}
