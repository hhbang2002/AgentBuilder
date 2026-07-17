# AgentBuilder

제조 도메인 Enterprise Agent 플랫폼(온프레미스 중심, 하이브리드 LLM). 문서:
`docs/01`(기능정의) · `docs/02`(설계) · `docs/02b`(UX) · `docs/02c`(DB) · `docs/03`(개발가이드/하네스).
지금 단계와 완료 기준은 `docs/03-development-guide.md` §5의 Stage 표를 본다.

## 명령어 (이것만 사용 — 직접 ruff/pytest/alembic 호출하지 말 것)

```
make verify        # fmt-check + lint + typecheck + import-linter + unit test — 커밋 전 필수, CI와 동일
make verify-fast    # git diff 대상 파일만 lint/typecheck (unit test는 전체 실행)
make fmt             # ruff format 적용
make test-int        # 통합 테스트 (make dev-up으로 인프라 먼저 기동)
make dev-up / dev-down  # 로컬 인프라(Postgres/Redis/Qdrant/MinIO/Keycloak/Ollama) 기동/중지
make db-migrate m="설명"  # Alembic 리비전 생성 (자동생성 아님 — 직접 작성)
make db-upgrade       # 최신 마이그레이션 적용
```

## 아키텍처 규칙 (import-linter가 강제 — 위반하면 `make verify`가 실패한다)

- 계층: `platform` ← `gateway`/`governance` ← `agents`/`knowledge`/`tools` ← `evals`/`deploy`
  (화살표 방향으로만 import 가능, platform은 어떤 기능 모듈도 모른다)
- 모듈 내부: `api`/`worker` → `service` → `adapters` → `ports` → `domain` (역방향 금지)
- `domain/`·`ports/`·`service/`는 langgraph·qdrant_client·litellm·docling·sqlalchemy·redis·
  fastapi 등 프레임워크/외부기술을 **직접 import할 수 없다** — 반드시 `adapters/`를 거친다
- 모듈 간 접근은 상대 모듈의 `service/` 공개 API로만 (내부 adapters·domain 직접 import 금지)
- 각 모듈 세부 규칙은 `src/agentbuilder/<module>/CLAUDE.md` 참고

## 스키마·DB 변경 순서 (반드시 이 순서로)

1. `src/agentbuilder/agents/domain/`(또는 해당 모듈) Pydantic 모델 먼저 수정
2. `make db-migrate m="..."`로 리비전 생성 → `migrations/versions/*.py`를 **직접** 작성
   (Alembic 자동생성 사용 안 함 — `migrations/env.py` 참고. 기존 리비전 파일 수정 금지,
   항상 새 리비전 추가)
3. `docs/02c-database-design.md`에 스키마 변경을 반영 — 문서가 코드와 어긋나면 다음
   세션이 잘못된 전제로 작업하게 된다

## 작업 방식

- 새 기능은 수락 기준(AC) 테스트부터 — `docs/03-development-guide.md` §5의 슬라이스별 AC
- 커밋 메시지에 FR 번호 표기 (예: `feat(knowledge): 하이브리드 검색 RRF [FR-KNW-03]`)
- 완료 기준: `make verify` 통과 + 해당 슬라이스 AC 테스트 통과. 실패한 채로 "일단 커밋"하지 말 것
- 안전 기본값 원칙: 정책류 필드(도구 실행 정책 등)는 항상 가장 제한적인 값을 기본값으로
  (`agents/domain/definition.py`의 `ToolPolicy.APPROVAL` 기본값이 예시)
- 템플릿(`templates/ehs/*.yaml`)은 DSL의 살아있는 예시이자 회귀 테스트 픽스처다 —
  DSL 스키마를 바꾸면 템플릿도 같이 갱신하고 `tests/unit/agents/domain/`을 재확인

## 하지 말 것

- `migrations/versions/`의 기존 파일 수정 (hook이 차단함 — 새 리비전을 추가할 것)
- `deploy/profiles/`에 실제 비밀값 커밋 (secret_ref로 참조만, 값은 시크릿 저장소)
- import-linter 계약을 우회하기 위한 `# noqa`/동적 import — 계약이 틀렸다면 계약 자체를 고칠 것
