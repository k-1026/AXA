// 웹 푸시 켜기·끄기 (결정 30, docs/backend-contracts.md 6-5절)
// 켜기: 알림 권한 → 서비스 워커(/sw.js) 등록 → 서버 공개 키로 구독 → 구독을 서버에 저장
// iOS(사파리)는 홈 화면에 추가한 앱에서만 푸시가 됨 → 그 밖에서는 'unsupported'
import { api, ApiError } from '../../components/api';

export type PushState = 'unsupported' | 'denied' | 'off' | 'on' | 'server-off';

export const pushSupported = () =>
  typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;

export const isIos = () => /iPad|iPhone|iPod/.test(navigator.userAgent);

const registration = () => navigator.serviceWorker.register('/sw.js');

async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.getRegistration('/sw.js');
  return reg ? reg.pushManager.getSubscription() : null;
}

export async function pushState(): Promise<PushState> {
  if (!pushSupported()) return 'unsupported';
  if (Notification.permission === 'denied') return 'denied';
  return (await currentSubscription()) ? 'on' : 'off';
}

// base64url → 구독에 넣는 바이트
function keyBytes(b64url: string): Uint8Array {
  const b64 = (b64url + '='.repeat((4 - (b64url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/');
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

export async function enablePush(token: string): Promise<PushState> {
  if (!pushSupported()) return 'unsupported';
  let key: string;
  try {
    key = (await api<{ public_key: string }>('/me/push/key', { token })).public_key;
  } catch (e) {
    if (e instanceof ApiError && e.code === 'push.unavailable') return 'server-off';
    throw e;
  }
  if ((await Notification.requestPermission()) !== 'granted') return 'denied';
  const reg = await registration();
  await navigator.serviceWorker.ready;
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key) }));
  const json = sub.toJSON();
  await api('/me/push/subscriptions', {
    method: 'POST',
    token,
    body: { endpoint: sub.endpoint, keys: { p256dh: json.keys?.p256dh ?? '', auth: json.keys?.auth ?? '' } },
  });
  return 'on';
}

// 끄기·로그아웃: 이 브라우저 구독을 풀고 서버에서도 지움 (같은 기기의 다음 사용자에게 앞 사람 알림이 가지 않게)
export async function disablePush(token: string | null): Promise<void> {
  const sub = await currentSubscription().catch(() => null);
  if (!sub) return;
  if (token) await api('/me/push/subscriptions', { method: 'DELETE', token, body: { endpoint: sub.endpoint } }).catch(() => {});
  await sub.unsubscribe().catch(() => false);
}
