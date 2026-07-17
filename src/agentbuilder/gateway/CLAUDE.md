# gateway (FR-MDL, Model Gateway)

**책임**: 모델 별칭 해석, 로컬/외부 LLM 라우팅, 데이터 등급 기반 정책 통제, 예산/사용량.
**소유 테이블**: 없음(설정은 `deployment_profiles`에 위임) + `model_usage`(쓰기 전용, evals/deploy 소유 아님 — gateway가 기록).
**공개 API**: `gateway.service`. LiteLLM은 **라이브러리로 내장**(별도 프록시 프로세스 아님,
ADR-03) — `adapters/`에서만 import.

## 현재 구현 상태 (Stage 0)

전 계층 미구현 (Stage 1 대상). 설계문서 §6.2 "정책 엔진 → 별칭 해석 → LiteLLM" 순서를
그대로 따를 것.

## 자주 하는 실수

- 정책(`PolicyEngine`)을 어댑터 호출 이후에 검사하면 안 됨 — 호출 전에 검사해야
  `dataClass: confidential`인데 외부 API로 나가는 사고를 막는다
- 에이전트/도구 코드가 `litellm`을 직접 import하면 안 됨 — 반드시 gateway 별칭을 거칠 것
  (import-linter가 domain/ports/service 계층에서는 이미 강제로 차단함)
