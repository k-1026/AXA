import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  initial?: string;
  onSubmit: (note: string) => void;
  onCancel?: () => void;
}

// "나의 경험"만 쓰는 칸. 병원·날짜는 방문 완료된 예약에서 자동으로 채워져 여기서 입력하지 않는다
// 점수·추천 입력은 두지 않는다 (후기가 아니라 개인 기록)
export function VisitForm({ initial, onSubmit, onCancel }: Props) {
  const { t } = useTranslation();
  const [note, setNote] = useState(initial ?? '');
  const [error, setError] = useState('');

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = note.trim();
    if (!text) return setError(t('mypage.visits.errNote'));
    setError('');
    onSubmit(text);
  };

  return (
    <form className="visit-form" onSubmit={submit} noValidate>
      <label className="visit-field">
        {t('mypage.visits.note')}
        <textarea
          rows={4}
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
