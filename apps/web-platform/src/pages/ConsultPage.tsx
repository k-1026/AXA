import { useEffect, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { MenuIcon, PlusIcon, SendIcon, TranslateIcon } from '../features/chatbot/icons';
import { useChatText } from '../features/chatbot/ChatMessages';
import { useVisualViewport } from '../features/chatbot/useVisualViewport';
import { CalendarIcon, InfoIcon } from '../features/mypage/icons';
import { useHospitals } from '../features/hospital/useHospitals';
import { ConsultSidebar } from '../features/consult/ConsultSidebar';
import { ConsultMessages } from '../features/consult/ConsultMessages';
import { BookingForm } from '../features/consult/BookingForm';
import { HospitalThumb } from '../features/consult/HospitalThumb';
import { ClipboardIcon } from '../features/consult/icons';
import { isConsultHours } from '../features/consult/format';
import { useConsultThreads } from '../features/consult/useConsultThreads';

const QUICK = [
  { key: 'booking', Icon: CalendarIcon },
  { key: 'interpret', Icon: TranslateIcon },
  { key: 'prepare', Icon: ClipboardIcon },
] as const;

// 병원 상담·예약. 병원마다 상담 하나 (1:1). 답변은 병원 담당자가 직접 한다
// 병원 상세의 "병원에 상담하기"로 들어오면 ?hospital=<id> 로 그 병원 상담을 연다
export function ConsultPage() {
  const { t } = useTranslation();
  const text = useChatText();
  const consult = useConsultThreads();
  const hospitals = useHospitals();
  const [params, setParams] = useSearchParams();
  const [drawer, setDrawer] = useState(false);
  const [form, setForm] = useState(false);
  const [draft, setDraft] = useState('');
  const [quickOpen, setQuickOpen] = useState(true);
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
    if (h) {
      consult.open({ hospitalId: h.id, name: { ko: h.name, en: h.nameEn }, dept: h.depts[0], district: h.district, photo: h.photo });
    }
    setParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, hospitals.status]);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setDrawer(false);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawer]);

  const active = consult.active;
  const open = consult.mode === 'demo' || isConsultHours();

  // 화면에 열려 있는 상담의 답변은 읽은 것으로 처리
  useEffect(() => {
    if (active?.unread) consult.select(active.hospitalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active?.hospitalId, active?.unread]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    consult.send(draft);
    setDraft('');
  };

  return (
    <div className={drawer ? 'chat-app consult-app is-drawer-open' : 'chat-app consult-app'}>
      <ConsultSidebar
        activeId={active?.hospitalId}
        search={consult.search}
        demo={consult.mode === 'demo'}
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
                  <span className={open ? 'consult-online is-on' : 'consult-online'}>{t(open ? 'consult.staffOnline' : 'consult.staffOffline')}</span>
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
                  onSubmit={(b) => {
                    consult.requestBooking(b);
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
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={t('consult.placeholder')}
                  aria-label={t('consult.placeholder')}
                  enterKeyHint="send"
                  autoComplete="off"
                />
                <button type="submit" className="chat-send" disabled={!draft.trim()} aria-label={t('consult.send')}>
                  <SendIcon />
                </button>
              </form>
              <p className="chat-disclaimer">{t('consult.hours')}</p>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
