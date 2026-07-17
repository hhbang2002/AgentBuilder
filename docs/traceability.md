# 요구사항 추적 매트릭스 (FR ↔ 구현 ↔ 테스트)

| 항목 | 내용 |
|---|---|
| 기준 문서 | [01-functional-specification.md](01-functional-specification.md) v0.3 |
| 갱신 방법 | `.claude/skills/spec-trace/SKILL.md` 절차. 수동 편집도 가능하나 커버리지 재계산은 스킬 절차를 따를 것 |
| 상태 값 | ⬜ 미구현 · 🟡 부분구현(코드는 있으나 테스트 미흡) · ✅ 테스트로 검증됨 |

이 문서는 **P0 요구사항만** 추적한다 (MVP 완료 기준 = 아래 표 전체가 ✅). P1/P2는
해당 Stage 착수 시 표에 추가한다.

## Stage 0 (하네스 & 스캐폴드)

| FR | 설명 | 모듈/파일 | 테스트 | 상태 |
|---|---|---|---|---|
| FR-AGT-01 | Agent Definition DSL 스키마 (JSON Schema 검증 포함). 실행 정책의 재시도 필드는 Stage 0 리뷰에서 누락 발견 → `RetryConfig`로 보완 완료 | `agents/domain/definition.py` | `tests/unit/agents/domain/test_definition.py` (`TestExecutionPolicy` 포함), `test_schema_export.py` | ✅ |
| FR-AGT-01 | GitOps 동기화용 정규화 YAML 직렬화 | `agents/domain/serde.py` | `test_definition.py::TestSerde` | ✅ |
| FR-GOV-01 | RBAC 표준 6역할 시드 (관리자/개발자/현업 편집자/검토자/뷰어/최종사용자 — FR 원문 목록과 1:1). ※ 01 §3 페르소나 6종과는 1:1이 아님(지식 관리자 페르소나는 별도 역할 없이 domain-editor에 포함, Stage 2 온톨로지 검수 구현 시 분리 여부 재검토) | `migrations/versions/0004_seed_core_data.py` | 시드 적용·왕복 psql 검증 (자동화는 Stage 1 리포지토리 계층에서) | 🟡 |
| FR-KNW-04 | ISA-95 설비 계층 온톨로지 스켈레톤 시드 (Enterprise→…→Equipment 6계층). 편집기·버전 관리는 P1 미착수 | `migrations/versions/0004_seed_core_data.py` | 시드 적용·계층 재귀 조회 psql 검증 | 🟡 |
| FR-AGT-02 | 컴파일 파이프라인 ③ 정적 검증(순환/미도달) — *컴파일러 자체(①②④)는 Stage 1* | `agents/domain/validation.py` | `test_validation.py` | 🟡 |
| FR-AGT-03 | 오케스트레이션 패턴 — DSL 노드 타입으로 표현 가능 (`llm`/`branch`/`parallel`/`subagent` 등), 실행은 Stage 1 | `agents/domain/definition.py::NodeType` | `test_definition.py::TestWorkflowKind` | 🟡 |
| FR-AGT-05 | HITL 게이트 — DSL `hitl-gate` 노드 표현. 실제 interrupt/재개는 Stage 1 | `agents/domain/definition.py::GraphNode`(approvers) | `test_hitl_gate_missing_approvers_is_rejected` | 🟡 |
| FR-AGT-07 | 구조화 출력 스키마 참조 — DSL `output.schema` 표현. 강제/재시도 로직은 Stage 1 | `agents/domain/definition.py::OutputConfig`, `StructuredOutputSpec` | `test_definition.py` | 🟡 |
| NFR-07 | 감사성 — 버전 불변성(insert-only) DB 강제 | `migrations/versions/0001_*.py` (트리거) | 수동 검증 완료(Stage 0 작업 중 psql로 확인), 자동화 테스트는 Stage 1 리포지토리 계층에서 | 🟡 |

### Stage 0 검토 이력 및 미검증 항목

- **2026-07-17 검토**: boundary-reviewer·spec-checker 서브에이전트 검토 완료. 반영:
  import-linter "service만 공개" 계약 7건 추가(+위반 감지 실증), `RetryConfig`(FR-AGT-01
  보완), FK 인덱스 리비전 0005(20건), 02c 문서 정합화(projects/outbox/chunks/파티셔닝
  유예), 본 매트릭스 정정.
- **미반영(사유 기록)**: ① 0004 downgrade의 SQL 문자열 포매팅(boundary-reviewer '참고') —
  하드코딩 상수만 사용해 인젝션 경로 없음. 기존 리비전 수정은 migration-guard가 차단하는
  규약이므로 코드 유지, 이후 리비전부터 `sa.text().bindparams()` 사용. ② 0004 docstring의
  "페르소나 매핑" 표현 부정확 — 동일 사유로 파일 유지, 정확한 사실관계는 위 FR-GOV-01
  행에 기록.
- **환경 제약으로 미검증**: `make dev-up` 전체 스택 헬스체크 — 개발 샌드박스가 컨테이너
  레지스트리(Docker Hub/quay.io) 접근을 차단하여 이미지 pull 불가. compose 구문 검증 및
  로컬 PostgreSQL 대상 마이그레이션 검증까지만 수행. **팀 환경 최초 `make dev-up` 시
  이미지 태그 확인·고정 필요** (dev.yml 헤더 주석 참고). Stage 0 DoD 중 이 항목만 조건부.

## Stage 1 이후 (착수 시 표 추가)

FR-AGT-01(컴파일러 ①②④), FR-AGT-02(컴파일러 본체), FR-AGT-04(체크포인트),
FR-AGT-05(interrupt/resume), FR-MDL-01/02, FR-OPS-01 등 — `docs/03-development-guide.md`
§5 Stage 1 AC 참고.

## 커버리지 요약

- P0 요구사항 총 개수: [기능정의서 §5 P0 표기 항목 수 — spec-trace 스킬 실행 시 재계산]
- ✅ 완료: 2 · 🟡 부분: 7 · ⬜ 미착수: 나머지 전체 (2026-07-17 검토 반영)
