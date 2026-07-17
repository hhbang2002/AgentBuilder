---
name: new-adapter
description: 기존 포트(추상 인터페이스)에 대한 새 어댑터를 추가하거나(예 Qdrant/LiteLLM/Docling 연동), 기존 어댑터를 다른 구현으로 교체할 때 사용한다. 설계문서 §11 확장 포인트 표에 있는 대상을 구현할 때, 또는 "~를 연동해줘", "이 벡터 DB를 Qdrant로 교체해줘" 같은 요청에 사용.
---

# 어댑터 추가/교체

설계문서([../../docs/02-architecture-design.md](../../docs/02-architecture-design.md)) §11
"확장 포인트 (포트/어댑터 카탈로그)" 표가 이 저장소의 포트 목록이다 — 새 어댑터를 만들기
전에 먼저 그 표에서 대상 포트가 이미 정의되어 있는지 확인한다.

## 절차

1. **포트 확인/정의**: `src/agentbuilder/<module>/ports/`에 대상 `Protocol`이 있는지 확인.
   없다면 먼저 정의한다 — 어댑터보다 포트가 먼저다. 포트 시그니처는 특정 라이브러리의
   타입을 노출하면 안 된다 (예: `VectorStorePort.search()`가 `qdrant_client.models.X`를
   반환하면 안 됨 — domain 타입이나 이 포트 전용 dataclass로 감쌀 것).
2. **어댑터 구현**: `src/agentbuilder/<module>/adapters/<tech>_<port>.py`에 클래스로 구현.
   외부 라이브러리 import는 이 파일 안에서만.
3. **포트 준수 테스트(conformance test) 작성**: 포트의 계약을 검증하는 테스트 스위트를
   포트 자체를 대상으로 파라미터화해서 작성한다 — 같은 테스트가 "fake 어댑터"와
   "실제 어댑터" 양쪽에 대해 통과해야 한다. 이렇게 하면:
   - service 계층 단위 테스트는 fake 어댑터로 빠르게 돈다
   - 실제 어댑터 테스트는 `tests/integration/`에 두고 `@pytest.mark.integration`으로
     표시 (make test-int, 인프라 필요)
   - 어댑터를 교체해도 같은 conformance 테스트로 회귀를 잡는다
4. **등록**: composition root(엔트리포인트의 의존성 조립 지점 — Stage 1부터 생김)에서
   어댑터 인스턴스를 생성해 service에 주입. 하드코딩된 `import`를 service/domain에
   흘리지 말 것.
5. **문서 갱신**: 새로운 포트 카테고리를 만들었다면 설계문서 §11 표에 행을 추가한다.
   기존 어댑터를 교체했다면 §10 오픈소스 스택 권고안의 선택 근거도 갱신할지 검토.
6. `make verify`로 계층/의존성 규칙 위반이 없는지 확인.

## 예시로 삼을 기존 패턴

Stage 0 시점에는 실제 어댑터가 아직 없다 — `src/agentbuilder/agents/domain/definition.py`의
`CompilerPort`류 설계 의도(설계문서 §6.1)를 참고해 시그니처를 얇고 domain 지향적으로
유지하는 스타일을 따를 것.
