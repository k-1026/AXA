import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useLocalized } from '../../lib/common';
import { useAuth } from '../../components/auth';
import { useNotifications, type Notice } from './NotificationsProvider';
import { disablePush, enablePush, isIos, pushState, type PushState } from './webPush';

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 9a6 6 0 0 1 12 0c0 6 2.5 7.5 2.5 7.5h-17S6 15 6 9" />
      <path d="M10 19.5a2 2 0 0 0 4 0" />
    </svg>
  );
}

// 헤더의 알림 종: 숫자 + 펼치면 목록. 누르면 그 화면으로 가고 읽은 것으로
export function NotificationBell() {
  const { t, i18n } = useTranslation();
  const text = useLocalized();
  const navigate = useNavigate();
  const { notices, markRead, markAll } = useNotifications();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);

  const label = (n: Notice) => {
    const hospital = n.hospital ? text(n.hospital) : t('notify.hospital');
    if (n.kind === 'status') return t(`notify.status.${n.status}`, { hospital });
    if (n.kind === 'reply') return t('notify.reply', { hospital, count: n.count });
    if (n.kind === 'reminder') return t(`notify.reminder.${n.status}`, { hospital });
    return t('notify.aftercare', { hospital, count: n.count });
  };
  const when = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language, { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="notify" ref={box}>
      <button
        type="button"
        className="header-button notify-button"
        aria-label={t('notify.open', { count: notices.length })}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <BellIcon />
        {notices.length > 0 && <span className="notify-count">{notices.length > 9 ? '9+' : notices.length}</span>}
      </button>
      {open && (
        <div className="notify-panel" role="dialog" aria-label={t('notify.title')}>
          <div className="notify-head">
            <strong>{t('notify.title')}</strong>
            {notices.length > 0 && (
              <button type="button" onClick={markAll}>
                {t('notify.markAll')}
              </button>
            )}
          </div>
          {notices.length === 0 ? (
            <p className="notify-empty">{t('notify.empty')}</p>
          ) : (
            <ul>
              {notices.map((n) => (
                <li key={n.key}>
                  <button
                    type="button"
                    onClick={() => {
                      markRead(n);
                      setOpen(false);
                      navigate(n.to);
                    }}
                  >
                    <span>{label(n)}</span>
                    {n.kind !== 'status' && <time dateTime={n.at}>{when(n.at)}</time>}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <PushToggle />
        </div>
      )}
    </div>
  );
}

// 이 기기에서 알림 받기 (웹 푸시, 결정 30) — 사이트를 닫아도 병원 소식을 알림으로
function PushToggle() {
  const { t } = useTranslation();
  const { token } = useAuth();
  const [state, setState] = useState<PushState | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    pushState().then(setState, () => setState('unsupported'));
  }, []);

  if (!token || state === null) return null;
  const toggle = async () => {
    setBusy(true);
    setFailed(false);
    try {
      if (state === 'on') {
        await disablePush(token);
        setState('off');
      } else setState(await enablePush(token));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };
  const note =
    state === 'unsupported' ? (isIos() ? 'notify.push.ios' : 'notify.push.unsupported')
    : state === 'denied' ? 'notify.push.denied'
    : state === 'server-off' ? 'notify.push.serverOff'
    : failed ? 'notify.push.failed'
    : state === 'on' ? 'notify.push.onNote' : 'notify.push.offNote';
  return (
    <div className="notify-push">
      <p>{t(note)}</p>
      {(state === 'on' || state === 'off') && (
        <button type="button" onClick={toggle} disabled={busy}>
          {t(state === 'on' ? 'notify.push.disable' : 'notify.push.enable')}
        </button>
      )}
    </div>
  );
}
