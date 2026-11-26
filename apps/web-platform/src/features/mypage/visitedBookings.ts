import { useConsultThreads } from '../consult/useConsultThreads';
import { displayStatus } from '../consult/types';

// 방문 기록에 자동으로 뜨는 병원: 예약 중 병원이 "방문 완료"로 표시한 건 (최근 방문 먼저)
export function useVisitedBookings() {
  const { bookings } = useConsultThreads();
  return bookings
    .filter((b) => displayStatus(b.booking) === 'visited')
    .sort((a, b) => `${b.booking.date}T${b.booking.time}`.localeCompare(`${a.booking.date}T${a.booking.time}`));
}
