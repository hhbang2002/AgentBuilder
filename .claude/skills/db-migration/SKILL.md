---
name: db-migration
description: 데이터베이스 스키마를 변경할 때(테이블/컬럼/인덱스/제약조건 추가·수정) 사용한다. Alembic 마이그레이션을 올바른 순서로 작성하고 검증하기 위한 절차. "테이블에 컬럼 추가해줘", "새 테이블 만들어줘" 같은 요청에 사용.
---

# DB 마이그레이션 작성

루트 [CLAUDE.md](../../CLAUDE.md)의 "스키마·DB 변경 순서"를 실행 가능한 절차로 푼 것이다.
**기존 리비전 파일은 수정할 수 없다** — `.claude/hooks/migration-guard.sh`가 Edit/Write를
구조적으로 차단한다. 새 리비전을 추가하는 것이 유일한 경로다.

## 절차

1. **먼저 도메인 모델을 바꾼다** (해당 스키마 변경이 어떤 domain Pydantic 모델과
   관련 있다면). DSL 자체 변경이면 `/new-node-type`처럼 별도 스킬을 따르고, 순수
   저장 계층 변경(인덱스 추가 등)이면 이 단계는 생략 가능.
2. **리비전 스켈레톤 생성**: `make db-migrate m="설명"` → `migrations/versions/` 아래
   자동생성 파일이 만들어진다. **자동생성된 `upgrade()`/`downgrade()` 본문은 비어
   있다** — `migrations/env.py`가 `target_metadata=None`이라 diff 자동생성을 쓰지
   않는다. 이 파일을 직접 채운다.
3. **기존 스타일을 따라 작성**: `migrations/versions/0001_core_platform_and_agents.py`가
   기준 패턴이다.
   - `_id_col()`, `_created_at_col()`, `_updated_at_col()` 같은 파일 로컬 헬퍼 재사용
     (마이그레이션 파일은 서로 독립적이어야 하므로 이 헬퍼들은 각 파일에 다시 정의한다
     — src의 모델을 import하지 않는다)
   - 가변 테이블에는 `_attach_updated_at_trigger(table)` 붙이기
   - insert-only 테이블(버전 이력류)에는 `_make_insert_only(table)` 붙이기
     (02c §1 불변성 규약)
   - UUID PK는 `pg.UUID(as_uuid=True)` + `server_default=sa.text("gen_random_uuid()")`
     (앱 계층에서 UUIDv7을 명시적으로 넣는 게 기본, 이건 seed/수동 SQL용 v4 폴백)
   - 인덱스: docs/02c §3 "인덱스 전략" 표를 먼저 확인 — 부분 인덱스가 필요한지
     (`postgresql_where=sa.text(...)`) 검토
4. **`downgrade()`도 반드시 작성** — `upgrade()`의 역순으로 테이블/함수를 drop.
   비워두지 말 것 (롤백 불가능한 마이그레이션은 배포 리스크).
5. **로컬 검증**:
   ```
   make db-upgrade      # 적용
   # psql로 직접 확인하거나, 트리거/제약조건이 의도대로 동작하는지 INSERT/UPDATE로 테스트
   make db-downgrade    # 되돌리기 — 에러 없이 깨끗하게 내려가야 함
   make db-upgrade       # 다시 head로
   ```
6. **`docs/02c-database-design.md` 갱신**: 새/변경된 테이블을 §2의 해당 절에 반영.
   문서와 마이그레이션이 어긋나면 다음 세션이 잘못된 스키마를 전제로 작업한다.
7. **`make verify`**: migrations/도 ruff+pyright 대상이다 (pyproject.toml
   `include`/`src` 목록 참고).

## 파티셔닝 관련

`runs`/`audit_logs`/`model_usage`는 Stage 0에서 의도적으로 일반 테이블로 만들었다
(02c §4 참고 — 트래픽이 실제로 문제될 때 파티션 전환 마이그레이션을 추가하는 게 더
저렴하다는 판단). 이 테이블들에 대규모 데이터 작업을 하기 전이라면 먼저 파티션 전환이
필요한지 검토할 것.
