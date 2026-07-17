---
name: new-node-type
description: Agent Definition DSL에 새로운 Workflow 그래프 노드 타입(예 llm/tool/retrieval/hitl-gate/subagent 외의 새 타입)을 추가할 때 사용한다. "새 노드 타입을 DSL에 추가해줘", "그래프에 X 타입 노드를 지원하게 해줘" 같은 요청에 사용.
---

# DSL 노드 타입 추가

DSL 노드 타입은 4곳이 동기화되어야 한다 — 하나라도 빠지면 스키마는 통과하는데 컴파일이나
캔버스에서 깨지는 노드가 생긴다. 설계문서
([../../docs/02-architecture-design.md](../../docs/02-architecture-design.md)) §6.1의
"노드 타입 → LangGraph 매핑" 표가 이 4곳의 근거다.

## 체크리스트 (순서대로)

1. **`src/agentbuilder/agents/domain/definition.py`**
   - `NodeType` enum에 새 값 추가
   - `_REQUIRED_FIELDS_BY_TYPE`에 이 타입이 요구하는 필수 필드 목록 추가
   - 새 필드가 필요하면 `GraphNode`에 필드 추가 (기존 노드 타입과 필드를 공유할 수 있으면
     재사용, 이 타입 전용이면 `XxxSpec` 모델을 만들어 타입 힌트를 명확히 할 것)
   - 노드 간 참조 무결성이 필요하면(예: 이 타입이 `spec.tools`나 `spec.knowledge`를
     참조) `AgentDefinition._check_graph_references_spec`에 검증 분기 추가 — 기존
     TOOL/RETRIEVAL 타입 처리를 참고
2. **`src/agentbuilder/agents/domain/__init__.py`**: 새로 추가한 심볼(Spec 모델 등)을
   export 목록에 추가
3. **`tests/unit/agents/domain/test_definition.py`**: 최소 두 케이스 추가
   - 정상 케이스: 새 노드 타입이 포함된 그래프가 파싱된다
   - 실패 케이스: 필수 필드 누락 시 `pydantic.ValidationError`가 발생한다
   (`TestNodeType.test_all_node_types_have_required_field_rules`는 자동으로 새 타입도
   커버하지만, 타입 고유의 검증 로직은 별도 테스트가 필요하다)
4. **`docs/02-architecture-design.md` §6.1 표**: 새 행 추가 — DSL 노드 → LangGraph 구현
   방식 매핑을 적어야 Stage 1 컴파일러 작업자가 무엇을 만들지 알 수 있다.
5. **(참고용, 지금 당장 구현 대상 아님)**
   - `agents/service`의 컴파일러(Stage 1)가 생기면 이 타입의 LangGraph 매핑을 구현
   - Studio 캔버스(Stage 5)가 생기면 노드 팔레트에 추가

## 검증

```
make verify   # ruff + pyright + import-linter + unit test
```

`templates/ehs/*.yaml`이 새 타입을 실제로 쓰는 예시가 되면 가장 좋다 — 스키마 변경이
살아있는 예시로 바로 검증된다.
