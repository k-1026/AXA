import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { MenuIcon, PlusIcon, SendIcon, TranslateIcon } from '../features/chatbot/icons';
import { useLocalized } from '../lib/common';
import { useVisualViewport } from '../features/chatbot/useVisualViewport';
import { CalendarIcon, InfoIcon } from '../features/mypage/icons';
import { useHospitals } from '../features/hospital/useHospitals';
import { ConsultSidebar } from '../features/consult/ConsultSidebar';
import { ConsultMessages } from '../features/consult/ConsultMessages';
import { BookingForm } from '../features/consult/BookingForm';
import { HospitalThumb } from '../features/consult/HospitalThumb';
import { ClipboardIcon } from '../features/consult/icons';
import { useConsultThreads } from '../features/consult/useConsultThreads';
import { hospitalNames } from '../features/hospital/name';
import { useMarkSeenOn } from '../features/notifications/NotificationsProvider';

const QUICK = [
  { key: 'booking', Icon: CalendarIcon },
  { key: 'interpret', Icon: TranslateIcon },
  { key: 'prepare', Icon: ClipboardIcon },
] as const;

// 병원 상담·예약. 병원마다 상담 하나 (1:1). 답변은 병원 담당자가 직접 한다
// 병원 상세의 "병원에 상담하기"로 들어오면 ?hospital=<id> 로 그 병원 상담을 연다
export function ConsultPage() {
  useMarkSeenOn('/booking'); // 이 화면을 열면 이 화면의 알림은 읽은 것으로
  const { t } = useTranslation();
  const text = useLocalized();
  const consult = useConsultThreads();
  const hospitals = useHospitals();
  const [params, setParams] = useSearchParams();
  const [drawer, setDrawer] = useState(false);
  const [form, setForm] = useState(false);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState('');
  const [quickOpen, setQuickOpen] = useState(true);
  const box = useRef<HTMLTextAreaElement>(null);

  // 입력한 줄 수만큼 높이를 늘림 (최대 높이는 화면 높이에 따라 CSS max-height, 넘으면 스크롤)
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [draft]);
  useVisualViewport();

  // 병원 상세·예약 관리에서 들어온 경우: 같은 병원 상담이 있으면 열고, 없으면 새로 만든다
  const wanted = params.get('hospital');
  useEffect(() => {
    if (!wanted) return;
    if (consult.threads.some((t) => t.hospitalId === wanted)) {
      consult.select(wanted);
      setParams({}, { replace: true });
      return;
    }
    if (hospitals.status !== 'ready') return;
    const h = hospitals.data.items.find((x) => x.id === wanted);
    if (h?.demo) { // 입점 안 한 실제 병원은 상담을 열지 않음 (요청을 보내도 not_joined 오류)
      consult.open({ hospitalId: h.id, name: hospitalNames(h), dept: h.depts[0], district: h.district, photo: h.photo });
    }
    setParams({}, { replace: true });
    // 주소의 병원 id나 병원 데이터 준비 상태가 바뀔 때만 실행. consult는 렌더마다 새 객체라 일부러 뺌 (넣으면 매번 다시 실행)
  }, [wanted, hospitals.status]);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setDrawer(false);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawer]);

  const active = consult.active;
  // "담당자 응답 가능" 표시는 데모에서만. 실제 회원 상담은 아직 병원이 답하는 기능이 연결되지 않았다
  const demo = consult.mode === 'demo';

  // 화면에 열려 있는 상담의 답변은 읽은 것으로 처리
  useEffect(() => {
    if (active?.unread) consult.select(active.hospitalId);
    // consult는 렌더마다 새 객체라 의존성에서 일부러 뺌 (열린 상담·안 읽은 수가 바뀔 때만 실행)
  }, [active?.hospitalId, active?.unread]);

  const sendDraft = async () => {
    if (!draft.trim() || sending || !consult.canSend) return;
    setSending(true);
    setSendError('');
    try {
      await consult.send(draft);
      setDraft('');
    } catch {
      setSendError(t('consult.sendFailed')); // 글은 그대로 두고 다시 보낼 수 있게
    } finally {
      setSending(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void sendDraft();
  };

  // Enter = 보내기, Shift+Enter = 줄바꿈 (챗봇과 같게). 한글 조합 중 Enter는 글자 확정이라 보내지 않음
  const onKeyDown = (e: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    void sendDraft();
  };

  return (
    <div className={drawer ? 'chat-app consult-app is-drawer-open' : 'chat-app consult-app'}>
      <ConsultSidebar
        activeId={active?.hospitalId}
        search={consult.search}
        demo={demo}
        onSelect={(id) => {
          consult.select(id);
          setForm(false);
          setDrawer(false);
        }}
        onClose={() => setDrawer(false)}
      />
      <div className="chat-scrim" onClick={() => setDrawer(false)} aria-hidden="true" />

      <section className="chat-main" aria-labelledby="consult-title">
        {!active ? (
          <div className="consult-start">
            <button type="button" className="chat-icon-button chat-menu-button" onClick={() => setDrawer(true)} aria-label={t('consult.openMenu')}>
              <MenuIcon />
            </button>
            <h1 id="consult-title">{t('nav.booking')}</h1>
            <p>{t('consult.start')}</p>
            <Link to="/hospitals" className="consult-button is-primary">
              {t('consult.findHospital')}
            </Link>
          </div>
        ) : (
          <>
            <div className="chat-title consult-title">
              <button
                type="button"
                className="chat-icon-button chat-menu-button"
                onClick={() => setDrawer(true)}
                aria-label={t('consult.openMenu')}
                aria-expanded={drawer}
              >
                <MenuIcon />
              </button>
              <HospitalThumb photo={active.photo} size="lg" />
              <div>
                <h1 id="consult-title">{text(active.name)}</h1>
                <p className="consult-meta">
                  {t(`dept.${active.dept}`)} · {t(`district.${active.district}`)}
                  {demo && <span className="consult-online is-on">{t('consult.staffOnline')}</span>}
                </p>
              </div>
              <div className="consult-head-actions">
                {!active.sample && (
                  <Link to={`/hospitals/${encodeURIComponent(active.hospitalId)}`} className="consult-button">
                    {t('consult.hospitalInfo')}
                  </Link>
                )}
                <button type="button" className="consult-button is-primary" aria-expanded={form} onClick={() => setForm(!form)}>
                  <CalendarIcon />
                  {t('consult.requestBooking')}
                </button>
              </div>
            </div>

            <p className="consult-notice">
              <InfoIcon />
              {t('consult.notice')}
            </p>

            <ConsultMessages thread={active} />

            <div className="chat-composer">
              {form && (
                <BookingForm
                  hospital={hospitals.status === 'ready' ? hospitals.data.items.find((x) => x.id === active.hospitalId) : undefined}
                  member={consult.mode === 'member'}
                  onSubmit={async (b, extra) => {
                    await consult.requestBooking(b, extra);
                    setForm(false);
                  }}
                  onCancel={() => setForm(false)}
                />
              )}
              {quickOpen && !form && (
                <div className="chat-quick" id="consult-quick">
                  {QUICK.map(({ key, Icon }) => (
                    <button key={key} type="button" onClick={() => (key === 'booking' ? setForm(true) : setDraft(t(`consult.quickText.${key}`)))}>
                      <Icon />
                      {t(`consult.quick.${key}`)}
                    </button>
                  ))}
                </div>
              )}
              <form className="chat-input" onSubmit={submit}>
                <button
                  type="button"
                  className="chat-input-plus"
                  aria-label={t('consult.quickMenu')}
                  aria-expanded={quickOpen}
                  aria-controls="consult-quick"
                  onClick={() => setQuickOpen(!quickOpen)}
                >
                  <PlusIcon />
                </button>
                <textarea
                  ref={box}
                  rows={1}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder={consult.canSend ? t('consult.placeholder') : t('consult.needBooking')}
                  aria-label={t('consult.placeholder')}
                  enterKeyHint="send"
                  autoComplete="off"
                  maxLength={2000} // 서버 질문 길이 한도
                  disabled={!consult.canSend}
                />
                <button type="submit" className="chat-send" disabled={!draft.trim() || sending || !consult.canSend} aria-label={t('consult.send')}>
                  <SendIcon />
                </button>
              </form>
              {sendError && <p className="chat-send-error" role="alert">{sendError}</p>}
              <p className="chat-disclaimer">{t('consult.hours')}</p>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
