# VOC 대시보드 · 검수 페이지

> 작성 2026-11-17 · 데이터: [../voc_classified.csv](../voc_classified.csv) · [../voc_tw_classified.csv](../voc_tw_classified.csv) · [../voc_ig_classified.csv](../voc_ig_classified.csv) (규칙 v6, [../voc_rules.md](../voc_rules.md))

| 페이지 | 링크 | 하는 일 |
|---|---|---|
| **메디대구 VOC 분류 현황** (대시보드) | https://claude.ai/artifact/RT4Ejz6ssbUbTsWYiGA63u | 분류표 3개를 합친 1,488건의 요약 수치, 원인 대분류 5개 × 출처, 여정 단계별, 세부 원인 순위(참고), 출처별 표, 필터로 거르는 댓글 목록 |
| **메디대구 VOC 검수** (검수 페이지) | https://claude.ai/artifact/4PD3ex4htBCBms6vNhuWVi | 무작위로 뽑은 댓글을 사람이 판정 기준을 보며 판정 → 모두 저장하면 Claude 판정과 일치율(출처별·칸별) 표시. 결과는 [../voc_review.md](../voc_review.md)에 기록 |
| **틱톡 VOC 14차 검수** (검수 페이지, 11/19 — 9차 4/20 · 10차 11/20 · 11차 13/20 · 12차 11/20 · 13차 9/20 미통과 뒤 새 20건, 이전 저장분은 `reviews`·`reviews10~13`) | https://claude.ai/artifact/5qTS6AQtLeBVNHfP3JB87r | 틱톡 3차 VOC 20건 ([../voc_review.md](../voc_review.md) 14차 준비의 대상 voc_id). 고를 때마다 판정자별로 자동 저장(`reviews/<판정자 id>`), 20건 제출 뒤에만 Claude 판정·일치율 공개. 다른 판정자의 진행 상황도 표시. Claude Code가 저장된 판정을 읽어 voc_review.md에 기록 — 코드 사본: [review_tiktok_14.html](review_tiktok_14.html) (이전: [9차](review_tiktok_9.html) · [10차](review_tiktok_10.html) · [11차](review_tiktok_11.html) · [12차](review_tiktok_12.html) · [13차](review_tiktok_13.html)) |
| **Threads·페이스북 VOC 15차 검수** (검수 페이지, 11/23) | https://claude.ai/artifact/682EJcHfZTUGowEq5GwRus | 4차 VOC(Threads 13 · 페이스북 7) 20건. 판정자별 자동 저장(`reviews15/<판정자 id>`), 20건 제출 뒤 결과 공개, 처음 제출 판정을 기록 — 코드 사본: [review_15_threads_facebook.html](review_15_threads_facebook.html) |

- 두 페이지 모두 claude.ai 아티팩트라 **공유 메뉴에서 공유해야** 팀원이 열 수 있음. 대시보드를 공유하면 첨부된 분류 데이터 전체를 볼 수 있음 (작성자 아이디는 없음)
- 대시보드 데이터는 CSV 3개를 합친 JSON 파일을 올린 것 → **분류표를 고치면 Claude Code가 파일을 다시 올려야** 반영됨
- "사람 검수 8차 20 / 20" 카드는 검수 결과를 직접 적은 고정값 → 다시 검수하면 고쳐야 함
- [dashboard_page.html](dashboard_page.html)은 대시보드 화면 코드 사본 (claude.ai 대시보드 안에서만 돌아감, 기록용)

## 지금 숫자 (2026-11-17)

| 항목 | 값 |
|---|---|
| 수집 | 1,488건 (유튜브 1,367 · 대만·대구 91 · 인스타그램 30) |
| 여정과 관련 | 803건 (판정 대상 1,452건의 55%) |
| 원인 대분류 | 가격 299 · 안전·통증·불신 191 · 시술 정보·효과·회복 115 · 병원 정보 111 · 한국 시술 기대·신뢰 87 |
| 대만·대구에서 1위 | 병원 정보 35건 / 89건 |
| 강도 2 이상 | 99건 |

## 출처

| 출처 | URL | 등급 | 기준 시점 | 확인일 |
|---|---|---|---|---|
| 유튜브·Dcard·인스타그램 댓글 | [../voc_rules.md](../voc_rules.md) · [../voc_대만대구.md](../voc_대만대구.md) 출처 표 | 개인 | 각 게시일 | 2026-11-17 |
