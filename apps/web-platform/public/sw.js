// 웹 푸시 서비스 워커 (결정 30). 사이트를 닫아도 병원 소식을 알림으로 보여 줌
// 서버는 종류·상태 코드·언어만 보냄 (글·건강정보·병원 이름 X) → 잠금 화면에도 민감한 내용이 보이지 않게 문장은 여기서 만듦
const TEXT = {
  ko: { title: '메디대구', status: '예약 상태가 바뀌었어요. 눌러서 확인해 주세요.', reply: '병원에서 상담 답장이 왔어요.', aftercare: '의료진이 사후관리 메시지를 보냈어요.', reminder48h: '병원 예약이 이틀 안으로 다가왔어요.', reminder24h: '병원 예약이 24시간 안으로 다가왔어요. 눌러서 확인해 주세요.', reminder2h: '병원 예약이 2시간 안으로 다가왔어요. 출발 전 위치를 확인해 주세요.' },
  en: { title: 'MediDaegu', status: 'Your booking status has changed. Tap to check.', reply: 'The hospital replied to your consultation.', aftercare: 'The medical team sent you an aftercare message.', reminder48h: 'Your hospital booking is within 2 days.', reminder24h: 'Your hospital booking is within 24 hours. Tap to check.', reminder2h: 'Your hospital booking is within 2 hours. Check the location before you leave.' },
  'zh-TW': { title: 'MediDaegu', status: '您的預約狀態已更新，請點擊查看。', reply: '醫院回覆了您的諮詢。', aftercare: '醫護人員傳來了術後管理訊息。', reminder48h: '距離您的醫院預約不到2天。', reminder24h: '距離您的醫院預約不到24小時，請點擊查看。', reminder2h: '距離您的醫院預約不到2小時，出發前請確認地點。' },
  'zh-CN': { title: 'MediDaegu', status: '您的预约状态已更新，请点击查看。', reply: '医院回复了您的咨询。', aftercare: '医护人员发来了术后管理消息。', reminder48h: '距离您的医院预约不到2天。', reminder24h: '距离您的医院预约不到24小时，请点击查看。', reminder2h: '距离您的医院预约不到2小时，出发前请确认地点。' },
  vi: { title: 'MediDaegu', status: 'Trạng thái đặt lịch của bạn đã thay đổi. Nhấn để xem.', reply: 'Bệnh viện đã trả lời yêu cầu tư vấn của bạn.', aftercare: 'Đội ngũ y tế đã gửi tin nhắn chăm sóc sau điều trị.', reminder48h: 'Lịch hẹn bệnh viện còn chưa đầy 2 ngày.', reminder24h: 'Lịch hẹn bệnh viện còn chưa đầy 24 giờ. Nhấn để xem.', reminder2h: 'Lịch hẹn bệnh viện còn chưa đầy 2 giờ. Hãy kiểm tra địa điểm trước khi đi.' },
  ja: { title: 'MediDaegu', status: '予約状況が更新されました。タップして確認してください。', reply: '病院から相談への返信が届きました。', aftercare: '医療スタッフからアフターケアのメッセージが届きました。', reminder48h: '病院の予約まで2日を切りました。', reminder24h: '病院の予約まで24時間を切りました。タップして確認してください。', reminder2h: '病院の予約まで2時間を切りました。出発前に場所をご確認ください。' },
};
const PAGE = { status: '/mypage/bookings', reply: '/booking', aftercare: '/aftercare', reminder: '/mypage/bookings' };

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = {};
  }
  const t = TEXT[data.lang] || TEXT.en;
  const kind = PAGE[data.kind] ? data.kind : 'status';
  event.waitUntil(
    self.registration.showNotification(t.title, {
      body: kind === 'reminder' ? t[`reminder${data.status}`] || t.reminder24h : t[kind],
      tag: `medidaegu-${data.request_id || kind}`, // 같은 예약 소식은 하나로 합침
      data: { url: PAGE[kind] },
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = new URL(event.notification.data?.url || '/', self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      const open = list.find((c) => c.url.startsWith(self.location.origin));
      if (open) return open.navigate(url).then((c) => (c || open).focus());
      return self.clients.openWindow(url);
    }),
  );
});
