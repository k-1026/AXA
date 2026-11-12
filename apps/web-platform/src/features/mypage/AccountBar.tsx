import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../components/auth';
import { ApiError } from '../../components/api';
import { GearIcon } from './icons';

// 내 계정: 탈퇴하기만 (프로필·언어 설정은 머리말 언어 선택으로)
export function AccountBar() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const demo = !!user?.demo;

  return (
    <section className="mp-card mp-account" aria-labelledby="mp-account-title">
      <GearIcon />
      <h2 id="mp-account-title">{t('mypage.account.title')}</h2>
      <span className="mp-account-spacer" />
      {demo && <small className="mp-account-note">{t('mypage.account.withdrawDemo')}</small>}
      <button type="button" className="mp-withdraw" disabled={demo} onClick={() => setOpen(true)}>
        {t('mypage.account.withdraw')}
      </button>
      {open && <WithdrawDialog onClose={() => setOpen(false)} />}
    </section>
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
