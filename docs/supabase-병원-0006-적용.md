# Supabase에 병원 테이블(0006) 적용·적재 — 실행 안내

> 2026-11-17 · 브랜치 `backend-A-hospital` · 실행: psycopg가 되는 팀원 PC (백엔드 A PC는 윈도우 앱 제어 정책에 psycopg DLL이 막힘)
> 무엇을: 마이그레이션 `0006`(hospitals·departments·hospital_departments·hospital_hours) + 공공데이터 4,242곳 적재
> PR 리뷰 전에 공용 DB에 먼저 넣는 것 → 리뷰에서 구조가 바뀌면 `downgrade 0005` 후 다시 적용

## 0. 준비

- 루트 `.env`의 `DATABASE_URL` = Supabase **세션 풀러(포트 5432)** 주소 (트랜잭션 풀러 6543은 마이그레이션에 쓰지 않음)
- 저장소 맨 위 폴더에서 실행. PowerShell·bash 둘 다 같은 명령

## 1. 브랜치와 데이터 파일

```
git fetch origin
git switch backend-A-hospital
git pull
git restore --source origin/research-data -- data/processed/daegu_registered_institutions.csv "data/raw/영업정보/daegu_dgsbjt_hospitals.json"
```

- 등록 유치의료기관·내과/안과 파일은 `research-data` 브랜치에만 있음. **`git show … > 파일`은 쓰지 말 것** — PowerShell 5.1에서 UTF-16으로 저장돼 등록 병원이 0곳이 됨. `git restore`는 원본 그대로 씀
- 확인: `data/processed/daegu_registered_institutions.csv` 첫 줄이 `registration_no,name_en,…`

## 2. 마이그레이션

```
uv run python -m alembic -c backend/alembic.ini current
uv run python -m alembic -c backend/alembic.ini upgrade head
```

- `current`가 `0005 (head)`가 아니면 멈추고 백엔드 A에게 알림 (다른 마이그레이션이 먼저 들어간 경우)
- `upgrade` 출력에 `Running upgrade 0005 -> 0006, 병원 공공정보 …`

## 3. 데이터 적재

```
uv run python backend/scripts/load_hospitals.py --dry-run
uv run python backend/scripts/load_hospitals.py
```

- 기대값: `{'loaded': 4242, 'registered': 126, 'closed': 0}`. `경고: … 없음`이 나오거나 `registered`가 0이면 1단계 파일 확인
- 다시 실행해도 됨 (ykiho로 덮어씀, id는 그대로)

## 4. 확인 (Supabase 대시보드 → SQL Editor)

```sql
select count(*) from hospitals;                                                         -- 4242
select count(*) from hospitals where is_registered_facility and status_verdict = 'normal'; -- 126
select count(*) from hospitals where status_verdict <> 'normal';                        -- 31 (폐업 9 + 미확인 22)
select dept_code, count(*) from hospital_departments group by 1 order by 1;
-- dermatology 80 · internal 1301 · ophthalmology 300 · plastic 70
select count(*) from hospital_hours;                                                    -- 29694
select relname, relrowsecurity from pg_class
 where relname in ('hospitals','departments','hospital_departments','hospital_hours');  -- 모두 true (RLS)
select version_num from alembic_version;                                               -- 0006
```

## 되돌리기

```
uv run python -m alembic -c backend/alembic.ini downgrade 0005
```

- 병원 4개 테이블과 데이터가 지워짐 (다른 테이블은 그대로)

## 끝나면

- 결과(4단계 숫자)를 슬랙에 남기기 → 백엔드 A가 `docs/backend-worklog-A.md`에 기록
- 배포 사이트(Vercel)에서 `/api/v1/hospitals`가 보이려면 이 브랜치가 backend → main으로 머지·배포돼야 함. 그 전에는 Supabase 대시보드와 이 브랜치를 로컬에서 띄운 경우에만 보임
