import { ApiError } from '../../components/api';

// 예약 요청 API 에러 → 번역 키 (docs/backend-contracts.md 4절)
export function bookingErrorKey(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === 'hospital.not_requestable') return e.detail.reason === 'not_joined' ? 'booking.err.notJoined' : 'booking.err.notRequestable';
    if (e.code === 'booking.duplicate') return 'booking.err.duplicate';
    if (e.code === 'consent.required') return 'booking.err.consentNeeded';
    if (e.code === 'residency.required') return 'residency.err.required';
    if (e.code === 'residency.not_eligible') return 'residency.err.notEligible';
    if (e.code === 'booking.invalid_transition') return 'booking.err.invalidTransition';
    if (e.code === 'validation') {
      const errs = Array.isArray(e.detail.errors) ? (e.detail.errors as { type?: string }[]) : [];
      return errs.some((x) => x.type === 'closed') ? 'consult.form.errClosed' : 'auth.err.validation';
    }
    if (e.code === 'network') return 'auth.err.network';
    if (e.code === 'auth.required') return 'booking.err.login';
  }
  if (e instanceof Error && e.message === 'hospital.not_requestable') return 'booking.err.notRequestable';
  if (e instanceof Error && e.message === 'residency.not_eligible') return 'residency.err.notEligible';
  return 'auth.err.unknown';
}
