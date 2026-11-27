// 지도 타일 주소·출처 (메인 지도·병원 상세가 같이 씀 — 업체를 바꿀 때 여기만 고침)
// OSM 타일 이용 정책 (https://operations.osmfoundation.org/policies/tiles/, 2026-11-27 확인):
// - 주소는 tile.openstreetmap.org 하나만 ({s}. 하위 주소는 느리거나 예고 없이 없어질 수 있음)
// - 출처는 지도 위에 "© OpenStreetMap contributors" 로 잘 보이게
// 시연용 무료 타일이라 보장 없음 → 실제 운영 전에는 타일 업체·자체 서버로 바꿀 것
export const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
