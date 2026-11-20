# simulation/ — 메디대구 2년 수익 시뮬레이션

요금안 v4로 24개월(Q1~Q8) 손익·현금흐름을 계산한다. 시장 검증 3단계 "돈이 남는가"(Day15).

| 파일 | 내용 |
|---|---|
| `pnl_sim.md` | **결과 요약** — 결론 한 줄, 근거 숫자, 판단 항목 6개, 지표 후보 |
| `output/profit_model.xlsx` | 수식이 살아 있는 시트 11개 (가정 노란 칸을 바꾸면 전부 다시 계산) |
| `output/수익시뮬레이션_대시보드.html` | 결과 대시보드 한 파일 (더블클릭으로 열림) |
| `output/images/` | 대시보드 이미지(PNG): 전체(인건비 250만, 세부 펼침) · 요약 3장(인건비 0원 / 250만 / 862.8만) |
| `verify.md` | 숫자 출처 검증 (자료 / 가정 구분) |
| `output/verify_formulas.md` | 엑셀 수식과 Python 계산 대조 결과 |
| `build_profit_model.py` | 엑셀·results.json·대시보드 파일 생성 |
| `verify_model.py` | 수식 검증 (`formulas` 패키지 필요) |
| `conclusions.json` | 대시보드 결론·주의 문구 |
| `dashboard/index.html` · `progress.py` | 작업 중 진행 상황 대시보드 (`.claude/launch.json`의 `simulation`, 포트 5176) |
| `source/` | 원본: 분석계획 md, 실습양식 엑셀·안내 md, Day15 PDF |

다시 만들기:

```bash
pip install openpyxl formulas
python3 simulation/build_profit_model.py
python3 simulation/verify_model.py
```
