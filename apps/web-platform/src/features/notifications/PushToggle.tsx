import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../components/auth';
import { disablePush, enablePush, isIos, pushState, type PushState } from './webPush';

// 이 기기에서 알림 받기 (웹 푸시, 결정 30) — 사이트를 닫아도 병원 소식을 알림으로
// - menu: 종 아이콘 안 (예전부터)
// - card: 예약 신청 완료 화면·마이페이지 (11/27 추가). 켜는 버튼이 종 안에만 있어서 구독이 0건이었음
//   onlyWhenOff면 이미 켰거나 쓸 수 없는 기기에서는 카드를 숨김 (예약 완료 화면이 시끄럽지 않게)
export function PushToggle({ variant = 'menu', onlyWhenOff = false }: { variant?: 'menu' | 'card'; onlyWhenOff?: boolean }) {
  const { t } = useTranslation();
  const { token, user } = useAuth();
  const [state, setState] = useState<PushState | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    pushState().then(setState, () => setState('unsupported'));
  }, []);

  if (!token || user?.demo || state === null) return null; // 예시 로그인은 서버 계정이 없음
  if (onlyWhenOff && state !== 'off' && !(state === 'unsupported' && isIos())) return null;
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
    <div className={variant === 'card' ? 'notify-push notify-push-card' : 'notify-push'}>
      {variant === 'card' && <strong className="notify-push-title">{t('notify.push.cardTitle')}</strong>}
      <p>{t(note)}</p>
      {(state === 'on' || state === 'off') && (
        <button type="button" onClick={toggle} disabled={busy}>
          {t(state === 'on' ? 'notify.push.disable' : 'notify.push.enable')}
        </button>
      )}
    </div>
  );
}
