import { useTranslation } from 'react-i18next';
import { localAddress } from './localize';

// 주소: 화면 언어로 옮긴 주소 + (한국어가 아니면) 한국어 원문을 작게. 택시·지도 앱에는 원문이 정확하다
export function HospitalAddress({ addr, original = true }: { addr: string; original?: boolean }) {
  const { i18n } = useTranslation();
  const shown = localAddress(addr, i18n.language);
  if (shown === addr) return <span lang="ko">{addr}</span>;
  return (
    <>
      <span>{shown}</span>
      {original && (
        <span className="addr-original" lang="ko">
          {addr}
        </span>
      )}
    </>
  );
}
