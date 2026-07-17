# tools (FR-TOL)

**책임**: 도구 레지스트리, 실행기(python/rest/sql/mcp), 커넥터 3계층 분리(ADR-08).
**소유 테이블**: `tool_definitions`, `connector_instances`, `semantic_schemas`.
**공개 API**: `tools.service`.

## 현재 구현 상태 (Stage 0)

전 계층 미구현 (Stage 3 대상).

## 3계층 분리 (ADR-08) — 절대 합치지 말 것

`ToolDefinition`(무엇을) → `ConnectorInstance`(어디에, 배포 프로파일 소유) →
`DeploymentProfile`. 도구 코드에 접속 정보를 하드코딩하면 고객사 배포마다 도구를 다시
만들어야 한다.

## 자주 하는 실수

- 커넥터는 기본이 읽기 전용(`read_only=true`) — 쓰기 도구는 실행 정책이 반드시
  `approval` 이상이어야 한다 (default_policy가 `auto`인 쓰기 도구를 만들지 말 것)
- Text-to-SQL 실행기는 SELECT 여부를 **프롬프트가 아니라 코드로** 검증할 것
  (파서 기반 검증 + 행 수 제한 + EXPLAIN 비용 상한, FR-TOL-04)
