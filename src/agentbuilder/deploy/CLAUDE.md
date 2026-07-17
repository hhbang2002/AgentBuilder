# deploy (FR-STD-05, FR-DEP)

**책임**: 버전 스냅샷, 환경 승격(품질 게이트 경유), 롤백, 배포 채널(API/웹챗/스케줄/이벤트).
**소유 테이블**: 없음 — `agents`(agents 모듈 소유)의 `deployments`를 다룬다.
`deployment_profiles`(platform 소유 개념이나 CRUD는 여기)를 조작.
**공개 API**: `deploy.service`.

## 현재 구현 상태 (Stage 0)

전 계층 미구현 (Stage 4~6 대상).

## 자주 하는 실수

- 버전 승격은 `evals.service`의 게이트 판정을 **먼저** 조회하고, 없으면 자동 트리거 —
  게이트를 건너뛰고 `deployments` 포인터를 직접 바꾸는 코드 경로를 만들지 말 것
- 승격은 `SELECT ... FOR UPDATE` + 단일 트랜잭션으로 (02c §5 동시성 규칙) — 경합 시
  두 승격이 동시에 성공하면 안 된다
