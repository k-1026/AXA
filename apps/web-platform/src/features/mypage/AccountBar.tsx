import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../components/auth';
import { ApiError } from '../../components/api';
import { emptyResidency, ResidencyQuestions } from '../residency/ResidencyQuestions';
import { GearIcon } from './icons';

// 내 계정: 체류 형태 다시 답하기(결정 28) · 탈퇴 (프로필·언어 설정은 머리말 언어 선택으로)
export function AccountBar() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [residencyOpen, setResidencyOpen] = useState(false);
  const demo = !!user?.demo;
  const residencyKey = user?.residency === 'short_term' ? 'shortTerm' : user?.residency === 'resident' ? 'resident' : 'none';

  return (
    <section className="mp-card mp-account" aria-labelledby="mp-account-title">
      <GearIcon />
      <h2 id="mp-account-title">{t('mypage.account.title')}</h2>
      {!demo && (
        <span className="mp-residency">
          {t('residency.status')}: <strong>{t(`residency.statusValue.${residencyKey}`)}</strong>
          <button type="button" className="mp-residency-edit" onClick={() => setResidencyOpen(true)}>
            {t('residency.edit')}
          </button>
        </span>
      )}
      <span className="mp-account-spacer" />
      {demo && <small className="mp-account-note">{t('mypage.account.withdrawDemo')}</small>}
      <button type="button" className="mp-withdraw" disabled={demo} onClick={() => setOpen(true)}>
        {t('mypage.account.withdraw')}
      </button>
      {open && <WithdrawDialog onClose={() => setOpen(false)} />}
      {residencyOpen && <ResidencyDialog onClose={() => setResidencyOpen(false)} />}
    </section>
  );
}

// 체류 형태 다시 답하기 (PUT /me/residency). 가입 때 안 답했거나 체류 상태가 바뀌었을 때
function ResidencyDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const { setResidency } = useAuth();
  const [answers, setAnswers] = useState(emptyResidency);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !busy && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await setResidency(answers);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError && err.code === 'network' ? 'auth.err.network' : 'auth.err.unknown');
      setBusy(false);
    }
  };

  return (
    <div className="mp-dialog-backdrop" onClick={() => !busy && onClose()}>
      <form className="mp-dialog" role="dialog" aria-modal="true" aria-label={t('residency.title')} onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <ResidencyQuestions value={answers} onChange={setAnswers} />
        {error && (
          <p className="auth-error" role="alert">
            {t(error)}
          </p>
        )}
        <div className="mp-dialog-actions">
          <button type="button" className="mp-login-secondary" onClick={onClose} disabled={busy}>
            {t('mypage.account.cancel')}
          </button>
          <button type="submit" className="mp-login-button" disabled={busy}>
            {busy ? t('auth.submitting') : t('residency.save')}
          </button>
        </div>
      </form>
    </div>
  );
}

function WithdrawDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const { withdraw } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !busy && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await withdraw(password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === 'auth.invalid_credentials'
          ? 'mypage.account.withdrawWrongPassword'
          : err instanceof ApiError && err.code === 'network'
            ? 'auth.err.network'
            : 'auth.err.unknown',
      );
      setBusy(false);
    }
  };

  return (
    <div className="mp-dialog-backdrop" onClick={() => !busy && onClose()}>
      <form
        className="mp-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mp-withdraw-title"
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
      >
        <h2 id="mp-withdraw-title">{t('mypage.account.withdrawTitle')}</h2>
        <p>{t('mypage.account.withdrawDesc')}</p>
        <label className="auth-field">
          <span>{t('mypage.account.withdrawPassword')}</span>
          <input
            ref={inputRef}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && (
          <p className="auth-error" role="alert">
            {t(error)}
          </p>
        )}
        <div className="mp-dialog-actions">
          <button type="button" className="mp-login-secondary" onClick={onClose} disabled={busy}>
            {t('mypage.account.cancel')}
          </button>
          <button type="submit" className="mp-withdraw-confirm" disabled={busy || !password}>
            {busy ? t('auth.submitting') : t('mypage.account.withdrawConfirm')}
          </button>
        </div>
      </form>
    </div>
  );
}
