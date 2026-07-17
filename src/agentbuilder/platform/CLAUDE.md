# platform (공통 인프라)

**책임**: 설정(env), DB 엔진, 큐(Redis/arq), 이벤트(아웃박스), 트레이싱 연결, 배포
프로파일 로더. **어떤 기능 모듈도 알지 못한다** (import-linter가 강제).
**소유 테이블**: `projects`, `deployment_profiles`, `outbox`.

## 현재 구현 상태 (Stage 0)

`adapters/settings.py`만 존재 — `Settings`/`get_settings()`. 나머지(큐 클라이언트,
DB 엔진 팩토리, 아웃박스 발행기)는 Stage 1에서 실제 사용처가 생길 때 추가한다
(사용처 없는 인프라 코드를 먼저 만들지 않는다).

## 자주 하는 실수

- `os.environ`을 직접 읽는 코드를 다른 모듈에 추가하지 말 것 — 설정 출처는
  `platform.adapters.settings.get_settings()` 하나로 고정 (배포 프로파일 전환을 위해)
- platform이 `agentbuilder.agents`류를 import하기 시작하면 계층이 무너진다 —
  공통으로 쓰고 싶은 로직이 특정 모듈에 있다면 그 모듈에서 platform으로 내리는 게 아니라
  platform에 새로 작성할 것
