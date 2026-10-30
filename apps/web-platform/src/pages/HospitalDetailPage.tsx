import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useHospitals } from '../features/hospital/useHospitals';
import type { Hospital } from '../features/hospital/types';

const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

export function HospitalDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const state = useHospitals();

  if (state.status === 'loading') return <p className="list-status">{t('map.loading')}</p>;
  if (state.status === 'error') return <p className="list-status">{t('map.error')}</p>;

  const h = state.data.items.find((x) => x.id === id);
  if (!h) {
    return (
      <section className="placeholder-page">
        <p>{t('hospital.notFound')}</p>
        <Link to="/hospitals">← {t('hospital.back')}</Link>
      </section>
    );
  }

  return (
    <article className="hospital-detail">
      {/* 목록에서 왔으면 뒤로 가기 (필터 유지), 주소로 바로 들어왔으면 목록으로 */}
      <Link
        to="/hospitals"
        className="back-link"
        onClick={(e) => {
          if (location.state?.fromList) {
            e.preventDefault();
            navigate(-1);
          }
        }}
      >
        ← {t('hospital.back')}
      </Link>

      <header className="detail-head">
        <div className="hospital-photo detail-photo" aria-hidden="true" />
        <div>
          <p className="hospital-type">{t(`hospitalType.${h.type}`, { defaultValue: h.type })}</p>
          <h1>{h.name}</h1>
          <ul className="dept-tags">
            {h.depts.map((d) => (
              <li key={d}>{t(`dept.${d}`)}</li>
            ))}
          </ul>
          <dl className="hospital-facts">
            <dt>{t('popup.addr')}</dt>
            <dd>{h.addr}</dd>
            <dt>{t('popup.tel')}</dt>
            <dd>{h.tel && <a href={`tel:${h.tel}`}>{h.tel}</a>}</dd>
            <dt>{t('hospital.homepage')}</dt>
            <dd>
              {h.url && (
                <a href={h.url} target="_blank" rel="noopener noreferrer">
                  {h.url}
                </a>
              )}
            </dd>
          </dl>
        </div>
      </header>

      <div className="detail-grid">
        <section className="detail-card">
          <h2>{t('hospital.hours')}</h2>
          <HoursTable hospital={h} />
          <p className="detail-note">{t('hospital.hoursNote')}</p>
        </section>

        <section className="detail-card">
          <h2>{t('hospital.facilities')}</h2>
          <dl className="hospital-facts">
            <dt>{t('hospital.emergencyDay')}</dt>
            <dd>{yesNo(t, h.emergencyDay)}</dd>
            <dt>{t('hospital.emergencyNight')}</dt>
            <dd>{yesNo(t, h.emergencyNight)}</dd>
            <dt>{t('hospital.parking')}</dt>
            <dd>{h.parking !== undefined ? t('hospital.parkingSpaces', { count: h.parking }) : ''}</dd>
            <dt>{t('hospital.parkingFee')}</dt>
            <dd>{yesNo(t, h.parkingFee)}</dd>
          </dl>
        </section>

        <section className="detail-card detail-map-card">
          <h2>{t('hospital.location')}</h2>
          <MapContainer center={[h.lat, h.lng]} zoom={16} className="detail-map">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <CircleMarker
              center={[h.lat, h.lng]}
              radius={9}
              pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#1f6feb', fillOpacity: 1 }}
            />
          </MapContainer>
        </section>
      </div>

      <p className="detail-source">
        {t('popup.source', { date: state.data.meta.fetchedAt.slice(0, 10) })}
      </p>
    </article>
  );
}

function yesNo(t: (k: string) => string, v: boolean | undefined) {
  if (v === undefined) return '';
  return v ? t('hospital.yes') : t('hospital.no');
}

function HoursTable({ hospital: h }: { hospital: Hospital }) {
  const { t } = useTranslation();
  // 요일별 시간이 없으면 일요일·공휴일 휴진 표시만 보여줌
  const closedText = (v?: string) => (v === 'closed' ? t('hospital.closed') : v ?? '');

  return (
    <table className="hours-table">
      <tbody>
        {DAY_KEYS.map((day, i) => {
          const slot = h.hours?.[i];
          let text = slot ? `${slot[0]} – ${slot[1]}` : '';
          if (!slot && day === 'sun') text = closedText(h.sunday);
          return (
            <tr key={day}>
              <th scope="row">{t(`day.${day}`)}</th>
              <td>{text}</td>
            </tr>
          );
        })}
        <tr>
          <th scope="row">{t('day.holiday')}</th>
          <td>{closedText(h.holiday)}</td>
        </tr>
        <tr>
          <th scope="row">{t('hospital.lunchWeek')}</th>
          <td>{h.lunchWeek ?? ''}</td>
        </tr>
        <tr>
          <th scope="row">{t('hospital.lunchSat')}</th>
          <td>{h.lunchSat ?? ''}</td>
        </tr>
        <tr>
          <th scope="row">{t('hospital.rcvWeek')}</th>
          <td>{h.rcvWeek ?? ''}</td>
        </tr>
        <tr>
          <th scope="row">{t('hospital.rcvSat')}</th>
          <td>{h.rcvSat ?? ''}</td>
        </tr>
      </tbody>
    </table>
  );
}
