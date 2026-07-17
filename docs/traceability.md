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
| FR-AGT-01 | Agent Definition DSL 스키마 (JSON Schema 검증 포함) | `agents/domain/definition.py` | `tests/unit/agents/domain/test_definition.py`, `test_schema_export.py` | ✅ |
| FR-AGT-01 | GitOps 동기화용 정규화 YAML 직렬화 | `agents/domain/serde.py` | `test_definition.py::TestSerde` | ✅ |
| FR-AGT-02 | 컴파일 파이프라인 ③ 정적 검증(순환/미도달) — *컴파일러 자체(①②④)는 Stage 1* | `agents/domain/validation.py` | `test_validation.py` | 🟡 |
| FR-AGT-03 | 오케스트레이션 패턴 — DSL 노드 타입으로 표현 가능 (`llm`/`branch`/`parallel`/`subagent` 등), 실행은 Stage 1 | `agents/domain/definition.py::NodeType` | `test_definition.py::TestWorkflowKind` | 🟡 |
| FR-AGT-05 | HITL 게이트 — DSL `hitl-gate` 노드 표현. 실제 interrupt/재개는 Stage 1 | `agents/domain/definition.py::GraphNode`(approvers) | `test_hitl_gate_missing_approvers_is_rejected` | 🟡 |
| FR-AGT-07 | 구조화 출력 스키마 참조 — DSL `output.schema` 표현. 강제/재시도 로직은 Stage 1 | `agents/domain/definition.py::OutputConfig`, `StructuredOutputSpec` | `test_definition.py` | 🟡 |
| NFR-07 | 감사성 — 버전 불변성(insert-only) DB 강제 | `migrations/versions/0001_*.py` (트리거) | 수동 검증 완료(Stage 0 작업 중 psql로 확인), 자동화 테스트는 Stage 1 리포지토리 계층에서 | 🟡 |

## Stage 1 이후 (착수 시 표 추가)

FR-AGT-01(컴파일러 ①②④), FR-AGT-02(컴파일러 본체), FR-AGT-04(체크포인트),
FR-AGT-05(interrupt/resume), FR-MDL-01/02, FR-OPS-01 등 — `docs/03-development-guide.md`
§5 Stage 1 AC 참고.

## 커버리지 요약

- P0 요구사항 총 개수: [기능정의서 §5 P0 표기 항목 수 — spec-trace 스킬 실행 시 재계산]
- ✅ 완료: 2 · 🟡 부분: 5 · ⬜ 미착수: 나머지 전체
