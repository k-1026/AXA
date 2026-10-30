import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { useTranslation } from 'react-i18next';
import 'leaflet/dist/leaflet.css';
import type { Hospital } from '../hospital/types';

const DAEGU_CENTER: [number, number] = [35.8714, 128.6014];

interface Props {
  hospitals: Hospital[];
  fetchedAt: string;
}

export function HospitalMap({ hospitals, fetchedAt }: Props) {
  const { t } = useTranslation();

  return (
    // preferCanvas: 병원 4천여 곳을 마커로 그려도 느려지지 않게
    <MapContainer center={DAEGU_CENTER} zoom={12} preferCanvas className="hospital-map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {hospitals.map((h) => (
        <CircleMarker
          key={h.id}
          center={[h.lat, h.lng]}
          radius={5}
          pathOptions={{ color: '#ffffff', weight: 1, fillColor: '#1f6feb', fillOpacity: 0.85 }}
        >
          <Popup>
            <strong>{h.name}</strong>
            <dl className="popup-info">
              <dt>{t('popup.type')}</dt>
              <dd>{t(`hospitalType.${h.type}`, { defaultValue: h.type })}</dd>
              <dt>{t('popup.addr')}</dt>
              <dd>{h.addr}</dd>
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
