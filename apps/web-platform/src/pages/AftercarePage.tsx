import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CloseIcon, MenuIcon, SendIcon } from '../features/chatbot/icons';
import { useChatText } from '../features/chatbot/ChatMessages';
import { useVisualViewport } from '../features/chatbot/useVisualViewport';
import { InfoIcon } from '../features/mypage/icons';
import { HospitalThumb } from '../features/consult/HospitalThumb';
import { bookingDateFull } from '../features/consult/format';
import { AftercareSidebar } from '../features/aftercare/AftercareSidebar';
import { AftercareMessages } from '../features/aftercare/AftercareMessages';
import { useAftercare } from '../features/aftercare/useAftercare';
import type { Attachment } from '../features/aftercare/types';

const MAX_FILES = 4;
const MAX_BYTES = 50 * 1024 * 1024; // 파일 1개당 50MB

// 사후 관리: 방문을 마친 예약(진료·시술)마다 그 병원 의료진과 대화. 상태 사진·영상 첨부 가능
export function AftercarePage() {
  const { t, i18n } = useTranslation();
  const text = useChatText();
  const care = useAftercare();
  const [drawer, setDrawer] = useState(false);
  const [draft, setDraft] = useState('');
  const [files, setFiles] = useState<Attachment[]>([]);
  const [error, setError] = useState('');
  const picker = useRef<HTMLInputElement>(null);
  useVisualViewport();

  const active = care.active;

  // 열려 있는 대화의 의료진 답변은 읽은 것으로 처리
  useEffect(() => {
    if (active?.unread) care.select(active.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active?.id, active?.unread]);

  // 다른 기록으로 옮기면 보내지 않은 첨부는 비운다
  useEffect(() => {
    setFiles([]);
    setError('');
  }, [active?.id]);

  const pick = (e: ChangeEvent<HTMLInputElement>) => {
    const chosen = Array.from(e.target.files ?? []);
    e.target.value = '';
    const ok: Attachment[] = [];
    for (const f of chosen) {
      const kind = f.type.startsWith('image/') ? 'image' : f.type.startsWith('video/') ? 'video' : null;
      if (!kind) return setError(t('aftercare.errType'));
      if (f.size > MAX_BYTES) return setError(t('aftercare.errSize'));
      ok.push({ kind, url: URL.createObjectURL(f), name: f.name });
    }
    if (files.length + ok.length > MAX_FILES) {
      ok.forEach((a) => URL.revokeObjectURL(a.url));
      return setError(t('aftercare.errCount', { max: MAX_FILES }));
    }
    setError('');
    setFiles([...files, ...ok]);
  };

  const removeFile = (url: string) => {
    URL.revokeObjectURL(url);
    setFiles(files.filter((f) => f.url !== url));
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!draft.trim() && !files.length) return;
    care.send(draft, files);
    setDraft('');
    setFiles([]);
    setError('');
  };

  return (
    <div className={drawer ? 'chat-app consult-app is-drawer-open' : 'chat-app consult-app'}>
      <AftercareSidebar
        visits={care.visits}
        activeId={active?.id}
        demo={care.mode === 'demo'}
        onSelect={(id) => {
          care.select(id);
          setDrawer(false);
        }}
        onClose={() => setDrawer(false)}
      />
      <div className="chat-scrim" onClick={() => setDrawer(false)} aria-hidden="true" />

      <section className="chat-main" aria-labelledby="aftercare-title">
        {!active ? (
          <div className="consult-start">
            <button type="button" className="chat-icon-button chat-menu-button" onClick={() => setDrawer(true)} aria-label={t('aftercare.openMenu')}>
              <MenuIcon />
            </button>
            <h1 id="aftercare-title">{t('nav.aftercare')}</h1>
            <p>{t('aftercare.start')}</p>
            <Link to="/mypage/bookings" className="consult-button is-primary">
              {t('consult.manageBookings')}
            </Link>
          </div>
        ) : (
          <>
            <div className="chat-title consult-title">
              <button
                type="button"
                className="chat-icon-button chat-menu-button"
                onClick={() => setDrawer(true)}
                aria-label={t('aftercare.openMenu')}
                aria-expanded={drawer}
              >
                <MenuIcon />
              </button>
              <HospitalThumb photo={active.thread.photo} size="lg" />
              <div>
                <h1 id="aftercare-title">{text(active.thread.name)}</h1>
                <p className="consult-meta">
                  {active.booking.treatment ? text(active.booking.treatment) : t(`dept.${active.thread.dept}`)} ·{' '}
                  {t('aftercare.visitedOn', { date: bookingDateFull(active.booking.date, active.booking.time, i18n.language) })}
                </p>
              </div>
              <span className="consult-status is-completed">{t('consult.status.completed')}</span>
            </div>

            <p className="consult-notice">
              <InfoIcon />
              {t('aftercare.notice')}
            </p>

            <AftercareMessages messages={active.messages} hospital={text(active.thread.name)} sample={active.thread.sample} />

            <div className="chat-composer">
              {files.length > 0 && (
                <ul className="aftercare-pending" aria-label={t('aftercare.pending')}>
                  {files.map((f) => (
                    <li key={f.url}>
                      {f.kind === 'image' ? <img src={f.url} alt={f.name} /> : <video src={f.url} muted preload="metadata" aria-label={f.name} />}
                      <button type="button" onClick={() => removeFile(f.url)} aria-label={t('aftercare.remove', { name: f.name })}>
                        <CloseIcon />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {error && (
                <p className="consult-form-error" role="alert">
                  {error}
                </p>
              )}
              <form className="chat-input" onSubmit={submit}>
                <input ref={picker} type="file" accept="image/*,video/*" multiple hidden onChange={pick} />
                <button type="button" className="chat-input-plus aftercare-attach" onClick={() => picker.current?.click()} aria-label={t('aftercare.attach')}>
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <rect x="3.5" y="6" width="17" height="13" rx="2" />
                    <circle cx="12" cy="12.5" r="3.2" />
                    <path d="M8.5 6l1.2-2h4.6l1.2 2" />
                  </svg>
                </button>
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder={t('aftercare.placeholder')}
                  aria-label={t('aftercare.placeholder')}
                  enterKeyHint="send"
                  autoComplete="off"
                />
                <button type="submit" className="chat-send" disabled={!draft.trim() && !files.length} aria-label={t('consult.send')}>
                  <SendIcon />
                </button>
              </form>
              <p className="chat-disclaimer">{t('aftercare.mediaNote')}</p>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
