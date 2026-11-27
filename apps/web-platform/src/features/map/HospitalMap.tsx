import { useEffect, useRef } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import { canvas, type CircleMarker as LeafletCircleMarker } from 'leaflet';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';
import { TILE_ATTRIBUTION, TILE_URL } from './tiles';
import { DEPARTMENT_COLORS } from '../hospital/filters';
import { useHospitalName } from '../hospital/name';
import type { DepartmentKey, Hospital } from '../hospital/types';
import { HospitalAddress } from '../hospital/HospitalAddress';

const DAEGU_CENTER: [number, number] = [35.8714, 128.6014];
const DAEGU_ZOOM = 12;
// 도트 크기(px 반지름)와 클릭 여유: 손가락·마우스로 잘 눌리게 도트를 키우고,
// 캔버스 렌더러 tolerance로 도트 바깥 몇 px까지 클릭으로 인정한다
const DOT_RADIUS = 8;
const DOT_RADIUS_FOCUS = 12;
const CLICK_TOLERANCE = 6;
const dotRenderer = canvas({ tolerance: CLICK_TOLERANCE });

// 검색 결과로 지도 이동: 1곳이면 확대 후 정보창 열기, 여러 곳이면 모두 보이게, 해제하면 처음 위치로
function FocusView({ focus, markers }: { focus: Hospital[] | null; markers: Map<string, LeafletCircleMarker> }) {
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
  const markers = useRef(new Map<string, LeafletCircleMarker>()).current;

  return (
    // preferCanvas: 병원 전체(수는 데이터에 따라 다름)를 마커로 그려도 느려지지 않게
    <MapContainer center={DAEGU_CENTER} zoom={DAEGU_ZOOM} preferCanvas renderer={dotRenderer} className="hospital-map">
      <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} />
      <FocusView focus={focus} markers={markers} />
      {hospitals.map((h) => (
        <CircleMarker
          key={h.id}
          ref={(m) => {
            if (m) markers.set(h.id, m);
            else markers.delete(h.id);
          }}
          center={[h.lat, h.lng]}
          radius={focus?.length === 1 ? DOT_RADIUS_FOCUS : DOT_RADIUS}
          // 필터를 골랐으면 그 진료과 색, 전체 보기면 대표 진료과 색
          pathOptions={{
            color: '#ffffff',
            weight: 1.5,
            fillColor: DEPARTMENT_COLORS[selectedDept ?? h.depts[0]],
            fillOpacity: 0.85,
          }}
        >
          <Popup>
            {/* 이름 줄 오른쪽(닫기 버튼 옆)에 병원 정보 바로 가기 */}
            <div className="popup-head">
              <strong>{nameOf(h)}</strong>
              <Link to={`/hospitals/${encodeURIComponent(h.id)}`} className="popup-detail">
                {t('popup.detail')}
              </Link>
            </div>
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
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
