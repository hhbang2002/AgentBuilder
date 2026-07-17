# agents (FR-AGT)

**책임**: Agent Definition DSL, DSL→LangGraph 컴파일, 실행(HITL/체크포인트 포함).
**소유 테이블**: `agents`, `agent_versions`(insert-only), `deployments`,
`prompt_templates`, `prompt_versions`(insert-only).
**공개 API**: `agents.service`의 유스케이스 함수만 다른 모듈이 import 가능.

## 현재 구현 상태 (Stage 0)

- `domain/definition.py`: DSL Pydantic 모델 — 완료. 예시는 `templates/ehs/*.yaml`.
- `domain/validation.py`: 그래프 순환/미도달 정적 검증 — 완료.
- `ports/`, `adapters/`, `service/`, `api/`, `worker/`: **아직 비어 있음 (Stage 1 대상)**.
  `CompilerPort`(→ LangGraph 어댑터), `RunEvent` 스트림은 설계문서 §6.1 참고.

## 자주 하는 실수

- `ToolBinding.policy` 기본값을 `auto`로 바꾸지 말 것 — 기본값은 항상 `approval`
  (안전 기본값 원칙, `test_tool_default_policy_is_approval_not_auto` 테스트가 감시)
- Workflow 그래프의 `tool`/`retrieval` 노드가 참조하는 이름은 반드시 `spec.tools`/
  `spec.knowledge`에 먼저 선언되어야 한다 (`AgentDefinition._check_graph_references_spec`)
- `agent_versions`는 insert-only — DB 트리거가 UPDATE/DELETE를 막는다. 수정이 필요하면
  새 버전을 만들 것
