---
name: new-module-part
description: agents/knowledge/tools/evals/deploy/gateway/governance/platform 중 한 모듈에 domain·ports·adapters·service·api·worker 계층 코드를 새로 추가할 때 표준 구조와 등록 절차를 따르기 위해 사용한다. "이 모듈에 서비스 로직을 추가해줘", "새 포트를 정의해줘" 같은 요청에 사용.
---

# 모듈 구성요소 추가

설계문서([../../docs/02-architecture-design.md](../../docs/02-architecture-design.md)) §3의
모듈 표준 구조를 따른다. 8개 모듈(`platform/agents/gateway/knowledge/tools/evals/governance/deploy`)
디렉토리와 6개 하위 계층(`domain/ports/adapters/service/api/worker`)은 Stage 0에서 이미
스캐폴드되어 있다 — 이 스킬은 그 안에 실제 코드를 넣을 때의 순서를 안내한다.

## 계층별 규칙 (한 줄 요약)

| 계층 | 담는 것 | 의존 가능 대상 |
|---|---|---|
| `domain/` | Pydantic 모델, 순수 로직·검증 | 표준 라이브러리 + pydantic만 |
| `ports/` | 추상 인터페이스(`typing.Protocol`) | domain만 |
| `adapters/` | 외부 기술 구현체 (DB/큐/LLM/...) | domain, ports, 외부 라이브러리 |
| `service/` | 유스케이스 함수 — **모듈의 공개 API** | domain, ports (adapters 직접 X, 의존성 주입으로 받음) |
| `api/` | FastAPI 라우터 | service |
| `worker/` | 큐 소비 핸들러 | service |

`domain/ports/service`에서 langgraph·qdrant_client·litellm·docling·sqlalchemy·redis·fastapi를
직접 import하면 `make verify`의 import-linter 단계가 실패한다 (`pyproject.toml`
`[[tool.importlinter.contracts]]` 참고) — 이건 설정 실수가 아니라 의도된 게이트다.

## 절차

1. **domain 먼저**: 새 개념이 필요하면 `domain/`에 Pydantic 모델부터 정의. 기존 예시:
   `src/agentbuilder/agents/domain/definition.py`(DSL), `validation.py`(정적 검증) —
   frozen 모델, `extra="forbid"`, 검증기로 불변식 강제하는 스타일을 따를 것.
2. **필요하면 port 정의**: 외부 기술에 의존하는 동작이면 `ports/`에 `Protocol`로 인터페이스
   선언. 이미 있는 포트를 구현만 하는 경우는 `/new-adapter` 스킬을 대신 사용할 것.
3. **service에 유스케이스 작성**: `service/`는 port(주입받은 인터페이스)와 domain 모델만
   사용해 유스케이스를 조합. 이 함수가 모듈의 "공개 API"이며 다른 모듈은 이 함수들만
   import한다 (계층 규칙 위반은 import-linter가 잡음).
4. **api/worker는 얇게**: `api/`의 FastAPI 라우터, `worker/`의 큐 핸들러는 입출력 변환과
   `service/` 호출만 — 비즈니스 로직을 여기 두지 말 것.
5. **테스트**: domain은 `tests/unit/<module>/domain/`, service는 fake 어댑터를 주입한
   `tests/unit/<module>/service/`에. 외부 서비스가 실제로 필요한 경로만
   `tests/integration/`(`@pytest.mark.integration`)로.
6. **검증**: `make verify`. 새 모듈에 처음 실제 코드가 들어가면 해당 모듈의
   `src/agentbuilder/<module>/CLAUDE.md`의 "현재 구현 상태" 절을 갱신할 것 (Stage 0
   시점 "미구현" 문구가 그대로 남아있으면 다음 세션이 잘못된 전제로 시작한다).
