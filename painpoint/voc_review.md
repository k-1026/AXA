# VOC 분류 사람 검수표 — 무작위 10건

> 작성 2026-11-13 · 대상: [voc_classified.csv](voc_classified.csv) · 기준: [voc_rules.md](voc_rules.md)
> 수업 기준: 무작위 10건을 사람이 다시 판정 → **불일치 3건 이상이면 판정 규칙을 고쳐 다시 분류**

## 하는 법

1. **아래 "원문"만 보고** 팀이 단계 · 유형 · 강도 · 원인 묶음을 직접 적는다 (Claude 판정은 맨 아래에 따로 있음. 먼저 보지 말 것)
2. 여정과 무관하면 "해당 없음"
3. 다 적은 뒤 맨 아래 Claude 판정과 비교해 "일치" 칸에 O/X
4. X가 3개 이상이면 다른 이유를 적고 Claude Code에 규칙 수정·재분류 요청

## 뽑은 방법

판정이 난 1,331건(크리에이터 제외)에서 **분류·검토 7건 + 해당 없음 3건**을 무작위로 뽑음 (Python `random.Random(20261113)`). 해당 없음도 섞은 이유: 제가 관련 있는 댓글을 빼먹었는지도 확인하려고.

## 팀 판정 (빈칸)

| # | voc_id | 원문 (번역) | 단계 | 유형 | 강도 | 원인 묶음 | 판정자 |
|---|---|---|---|---|---|---|---|
| 1 | Y1-012 | "In South Korea, people legally are not allowed to disclose the names of clinics they went to or how much they paid for the treatments (unless if they have a sponsorship…). I'm not sure how that extends to foreign travellers but it could be a reason why its often not disclosed." (한국에선 다녀온 병원 이름·가격을 법적으로 공개 못 해서 안 알려주는 것 같다) | | | | | |
| 2 | Y1-023 | "…Prices will vary based off of many different factors (ie foreigner "tax" being charged more than locals, skin condition, treatment recommendations, clinic location, promotions, interpreter services etc)… it makes more sense to direct the general public to contact the clinic directly to request for a quote" (가격은 외국인 추가 요금·피부 상태·통역 등으로 달라지니 클리닉에 직접 견적을 받는 게 맞다) | | | | | |
| 3 | Y3-017 | "I wonder how they come up with this "skin age"… I expect "skin age" is calculated for each customer as their real age + however much they think they can sell." (피부 나이는 실제 나이 + 팔 수 있을 만큼 더한 숫자 같다) | | | | | |
| 4 | Y3-091 | "That mask application was perfection 🙌🙌🙌" (마스크 바르는 솜씨가 완벽하다) | | | | | |
| 5 | Y3-175 | "That's so awesome! What's the apprenticeship?" (멋지다, 무슨 견습이야?) | | | | | |
| 6 | Y3-183 | "I would love to do it too. Bit the question how much it costs? ❤" (나도 받고 싶은데 얼마야?) | | | | | |
| 7 | Y3-267 | "I wish you told us how much it all costs😂" (전부 얼마였는지 알려줬으면) | | | | | |
| 8 | Y3-593 | "Whose stem cells?? There are no stem cells in healthy normal blood. Fact." (누구 줄기세포? 정상 혈액엔 줄기세포가 없다) | | | | | |
| 9 | Y5-168 | "Can you give us the doctor's name, address, and phone number? The surgery is very natural. I want to have it done too." (의사 이름·주소·전화번호를 알려달라, 나도 받고 싶다) | | | | | |
| 10 | Y6-028 | "ありがとう❤" (고마워) | | | | | |

## 결과

| 항목 | 값 |
|---|---|
| 일치 | __ / 10 |
| 불일치 | __ 건 |
| 규칙 수정 필요 (3건 이상) | 예 / 아니오 |
| 검수일 · 판정자 | |

---

<details>
<summary>Claude 판정 (팀 판정을 다 적은 뒤 열기)</summary>

| # | voc_id | 단계 | 유형 | 강도 | 원인 묶음 | 일치 (O/X) | 다른 이유 |
|---|---|---|---|---|---|---|---|
| 1 | Y1-012 | ① 알아보기 | 불만 | 1 | 병원 정보 공유 제약 | | |
| 2 | Y1-023 | ② 비교·결정 | 불만 | 1 | 외국인 가격·결제 불신 | | |
| 3 | Y3-017 | ④ 방문·진료 | 불만 | 2 | 상술·과잉 진단 불신 | | |
| 4 | Y3-091 | 해당 없음 | | | | | |
| 5 | Y3-175 | 해당 없음 | | | | | |
| 6 | Y3-183 | ② 비교·결정 | 질문 | 1 | 가격 정보 없음 | | |
| 7 | Y3-267 | ② 비교·결정 | 불만 | 1 | 가격 정보 없음 | | |
| 8 | Y3-593 | ② 비교·결정 | 불만 | 1 | 광고·과장 정보 불신 | | |
| 9 | Y5-168 | ① 알아보기 | 질문 | 1 | 병원 이름·위치 정보 없음 | | |
| 10 | Y6-028 | 해당 없음 | | | | | |

</details>

## 출처

| 출처 | URL | 등급 | 기준 시점 | 확인일 |
|---|---|---|---|---|
| 유튜브 댓글 (Y1·Y3·Y5·Y6) | [voc_rules.md](voc_rules.md) 출처 표 | 개인 | 각 영상 게시일 | 2026-11-13 |
| 검수 방법 | Day11 강의 자료 19쪽 (표본 검수 10건 · 불일치 3건 기준) | 공식(강의) | 2026-11-09 | 2026-11-13 |
