import { useEffect, useRef } from 'react';
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import { canvas, divIcon, type Layer } from 'leaflet';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';
import { DEPARTMENT_COLORS } from '../hospital/filters';
import { useHospitalName } from '../hospital/name';
import type { DepartmentKey, Hospital } from '../hospital/types';
import { HospitalAddress } from '../hospital/HospitalAddress';
import { membershipOf, type Membership } from '../hospital/membership';

const DAEGU_CENTER: [number, number] = [35.8714, 128.6014];
const DAEGU_ZOOM = 12;
// 도트 크기(px 반지름)와 클릭 여유: 손가락·마우스로 잘 눌리게 도트를 키우고,
// 캔버스 렌더러 tolerance로 도트 바깥 몇 px까지 클릭으로 인정한다
const DOT_RADIUS = 8;
const DOT_RADIUS_FOCUS = 12;
const CLICK_TOLERANCE = 6;
const dotRenderer = canvas({ tolerance: CLICK_TOLERANCE });

// 입점 병원 = 흰 바탕 원 안의 병원 십자 (진료과 색), 프리미엄 회원은 테두리가 네모 (styles.css .partner-pin)
// 크기는 일반 점(지름 16px)보다 조금 크게. 점(캔버스)과 달리 HTML 마커라 항상 점들 위에 보인다
const PIN_SIZE = 20;
const PIN_SIZE_FOCUS = 28;

function partnerIcon(color: string, membership: Exclude<Membership, null>, focused: boolean) {
  const size = focused ? PIN_SIZE_FOCUS : PIN_SIZE;
  const frame =
    membership === 'premium'
      ? `<rect x="2" y="2" width="28" height="28" rx="4" fill="#fff" stroke="${color}" stroke-width="3"/>`
      : `<circle cx="16" cy="16" r="14" fill="#fff" stroke="${color}" stroke-width="3"/>`;
  return divIcon({
    className: `partner-pin${membership === 'premium' ? ' is-premium' : ''}`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
    html: `<svg viewBox="0 0 32 32" aria-hidden="true">${frame}<path d="M13 7h6v6h6v6h-6v6h-6v-6H7v-6h6z" fill="${color}"/></svg>`,
  });
}

// 검색 결과로 지도 이동: 1곳이면 확대 후 정보창 열기, 여러 곳이면 모두 보이게, 해제하면 처음 위치로
function FocusView({ focus, markers }: { focus: Hospital[] | null; markers: Map<string, Layer> }) {
  const map = useMap();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (!focus) {
      map.closePopup();
      map.setView(DAEGU_CENTER, DAEGU_ZOOM);
    } else if (focus.length === 1) {
      const h = focus[0];
      map.setView([h.lat, h.lng], 17);
      // 마커가 지도에 붙은 뒤에 정보창을 연다
      setTimeout(() => markers.get(h.id)?.openPopup(), 0);
    } else if (focus.length > 1) {
      map.fitBounds(focus.map((h) => [h.lat, h.lng] as [number, number]), { padding: [40, 40], maxZoom: 16 });
    }
  }, [focus, map, markers]);
  return null;
}

interface Props {
  hospitals: Hospital[];
  fetchedAt: string;
  selectedDept: DepartmentKey | null;
  focus?: Hospital[] | null;
}

export function HospitalMap({ hospitals, fetchedAt, selectedDept, focus = null }: Props) {
  const { t } = useTranslation();
  const nameOf = useHospitalName();
  const markers = useRef(new Map<string, Layer>()).current;
  const keep = (id: string) => (m: Layer | null) => {
    if (m) markers.set(id, m);
    else markers.delete(id);
  };
  const colorOf = (h: Hospital) => DEPARTMENT_COLORS[selectedDept ?? h.depts[0]];
  // 입점 병원은 점 대신 십자 마커로, 나중에 그려 위에 오게
  const plain = hospitals.filter((h) => !membershipOf(h));
  const partners = hospitals.filter((h) => membershipOf(h));

  const popup = (h: Hospital) => {
    const membership = membershipOf(h);
    return (
      <Popup>
        {/* 이름 줄 오른쪽(닫기 버튼 옆)에 병원 정보 바로 가기 */}
        <div className="popup-head">
          <strong>{nameOf(h)}</strong>
          <Link to={`/hospitals/${encodeURIComponent(h.id)}`} className="popup-detail">
            {t('popup.detail')}
          </Link>
        </div>
        {membership && (
          <p className="popup-badges">
            <span className="popup-badge">{t('popup.partner')}</span>
            {membership === 'premium' && (
              // 설명은 평소에 숨기고 커서를 대거나 키보드로 초점을 줄 때만
              <span className="popup-badge is-premium" tabIndex={0} aria-describedby={`premium-tip-${h.id}`}>
                {t('popup.premium')}
                <span id={`premium-tip-${h.id}`} role="tooltip" className="popup-tip">
                  {t('popup.premiumTip')}
                </span>
              </span>
            )}
          </p>
        )}
        <dl className="popup-info">
          <dt>{t('popup.type')}</dt>
          <dd>{t(`hospitalType.${h.type}`, { defaultValue: h.type })}</dd>
          <dt>{t('popup.addr')}</dt>
          <dd><HospitalAddress addr={h.addr} /></dd>
          {h.tel && (
            <>
              <dt>{t('popup.tel')}</dt>
              <dd>
                <a href={`tel:${h.tel}`}>{h.tel}</a>
              </dd>
            </>
          )}
        </dl>
        <p className="popup-source">
          {t('popup.source', { date: fetchedAt.slice(0, 10) })}
        </p>
      </Popup>
    );
  };

  return (
    // preferCanvas: 병원 전체(수는 데이터에 따라 다름)를 마커로 그려도 느려지지 않게
    <MapContainer center={DAEGU_CENTER} zoom={DAEGU_ZOOM} preferCanvas renderer={dotRenderer} className="hospital-map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FocusView focus={focus} markers={markers} />
      {plain.map((h) => (
        <CircleMarker
          key={h.id}
          ref={keep(h.id)}
          center={[h.lat, h.lng]}
          radius={focus?.length === 1 ? DOT_RADIUS_FOCUS : DOT_RADIUS}
          // 필터를 골랐으면 그 진료과 색, 전체 보기면 대표 진료과 색
          pathOptions={{ color: '#ffffff', weight: 1.5, fillColor: colorOf(h), fillOpacity: 0.85 }}
        >
          {popup(h)}
        </CircleMarker>
      ))}
      {partners.map((h) => (
        <Marker
          key={h.id}
          ref={keep(h.id)}
          position={[h.lat, h.lng]}
          icon={partnerIcon(colorOf(h), membershipOf(h)!, focus?.length === 1)}
          zIndexOffset={membershipOf(h) === 'premium' ? 1000 : 500}
          title={nameOf(h)}
        >
          {popup(h)}
        </Marker>
      ))}
    </MapContainer>
  );
}
