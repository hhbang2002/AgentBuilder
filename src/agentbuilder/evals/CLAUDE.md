# evals (FR-EVL)

**책임**: 골든셋 관리, 평가 실행(rule/LLM-judge/RAG 지표), 품질 게이트 판정.
**소유 테이블**: `datasets`, `dataset_items`, `eval_runs`, `eval_results`, `quality_gates`.
**공개 API**: `evals.service`. **품질 게이트 판정 로직은 여기 있지만, "승격을 막을지"
결정은 `deploy` 모듈이 호출한다** (evals는 판정만, 승격 자체는 소유하지 않음).

## 현재 구현 상태 (Stage 0)

전 계층 미구현 (Stage 4 대상).

## 자주 하는 실수

- 평가 실행도 일반 에이전트 실행과 동일한 `RunEvent`/트레이스 경로를 재사용할 것 —
  평가 전용 트레이싱을 새로 만들지 말 것 (실패 케이스 드릴다운이 공짜로 얻어지는 이유)
- Evaluator는 플러그인(`EvaluatorPort`)으로 추가 — `service/` 안에 특정 평가 로직을
  하드코딩하지 말 것
