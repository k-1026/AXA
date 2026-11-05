import { useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { matchHospitals } from '../map/HospitalSearch';
import { useHospitalName } from '../hospital/name';
import type { Hospital } from '../hospital/types';
import type { VisitInput } from './visitLog';

const MAX_SUGGESTIONS = 8;

// 방문 날짜 기본값은 오늘 (한국 시간)
const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date());

interface Props {
  hospitals: Hospital[];
  initial?: VisitInput;
  onSubmit: (input: VisitInput) => void;
  onCancel?: () => void;
}

// 병원은 목록에서 고르거나 직접 입력한다. 점수·추천 입력은 두지 않는다 (후기가 아니라 개인 기록)
export function VisitForm({ hospitals, initial, onSubmit, onCancel }: Props) {
  const { t } = useTranslation();
  const nameOf = useHospitalName();
  const [hospitalName, setHospitalName] = useState(initial?.hospitalName ?? '');
  const [hospitalId, setHospitalId] = useState(initial?.hospitalId);
  const [date, setDate] = useState(initial?.date ?? today());
  const [note, setNote] = useState(initial?.note ?? '');
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');

  const suggestions = useMemo(
    () =>
      matchHospitals(hospitals, hospitalName)
        .sort((a, b) => nameOf(a).localeCompare(nameOf(b)))
        .slice(0, MAX_SUGGESTIONS),
    [hospitals, hospitalName, nameOf],
  );

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const name = hospitalName.trim();
    const text = note.trim();
    if (!name) return setError(t('mypage.visits.errHospital'));
    if (!date || date > today()) return setError(t('mypage.visits.errDate'));
    if (!text) return setError(t('mypage.visits.errNote'));
    setError('');
    onSubmit({ hospitalId, hospitalName: name, date, note: text });
    if (!initial) {
      setHospitalName('');
      setHospitalId(undefined);
      setDate(today());
      setNote('');
    }
  };

  return (
    <form className="visit-form" onSubmit={submit} noValidate>
      <div className="visit-form-row">
        <label className="visit-field visit-hospital">
          {t('mypage.visits.hospital')}
          <input
            type="text"
            value={hospitalName}
            placeholder={t('mypage.visits.hospitalPlaceholder')}
            autoComplete="off"
            onChange={(e) => {
              setHospitalName(e.target.value);
              setHospitalId(undefined);
              setOpen(true);
              setError('');
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
          />
          {open && suggestions.length > 0 && (
            <ul className="map-search-list">
              {suggestions.map((h) => (
                <li key={h.id}>
                  {/* onMouseDown: input blur보다 먼저 처리 */}
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      setHospitalName(nameOf(h));
                      setHospitalId(h.id);
                      setOpen(false);
                      setError('');
                    }}
                  >
                    <strong>{nameOf(h)}</strong>
                    <span lang="ko">{h.addr}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </label>
        <label className="visit-field">
          {t('mypage.visits.date')}
          <input type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} />
        </label>
      </div>
      <label className="visit-field">
        {t('mypage.visits.note')}
        <textarea
          rows={5}
          maxLength={2000}
          value={note}
          placeholder={t('mypage.visits.notePlaceholder')}
          onChange={(e) => {
            setNote(e.target.value);
            setError('');
          }}
        />
      </label>
      {error && (
        <p className="visit-error" role="alert">
          {error}
        </p>
      )}
      <div className="visit-actions">
        {onCancel && (
          <button type="button" className="visit-button" onClick={onCancel}>
            {t('mypage.visits.cancel')}
          </button>
        )}
        <button type="submit" className="visit-button is-primary">
          {t(initial ? 'mypage.visits.update' : 'mypage.visits.save')}
        </button>
      </div>
    </form>
  );
}
