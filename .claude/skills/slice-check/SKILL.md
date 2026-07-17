---
name: slice-check
description: 현재 개발 단계(Stage)의 수락 기준(AC)이 충족됐는지 점검하거나, 다음 Stage로 넘어가도 되는지 확인할 때 사용한다. "이번 슬라이스 끝났는지 확인해줘", "Stage 1 시작해도 돼?", "AC 통과했어?" 같은 요청에 사용.
---

# 슬라이스(Stage) 완료 점검

`.claude/STAGE` 파일이 현재 진행 중인 Stage 번호를 담는다 (Stage 0 = 하네스/스캐폴드,
이 파일 자체가 그 산출물 중 하나다). Stage 정의와 AC는
[../../docs/03-development-guide.md](../../docs/03-development-guide.md) §5 표에 있다.

## 절차

1. `.claude/STAGE`를 읽어 현재 Stage 번호 확인
2. `docs/03-development-guide.md` §5에서 해당 Stage 행의 "범위"와 "AC" 열을 찾는다
3. **자동 검증 가능한 것부터 실행**:
   ```
   make verify        # 모든 Stage 공통 — 이게 실패하면 AC를 논할 필요도 없다
   make test-int       # Stage 2 이상 + 통합 테스트가 존재하는 경우
   ```
4. **AC 항목별로 자동/수동 여부를 구분해 하나씩 확인**. 이 저장소는 아직 Stage별
   전용 E2E 테스트 스위트(`tests/e2e/`)가 없다 (Stage 5~6에서 Playwright 기반으로
   추가 예정, docs/03 §4) — 그전까지는 AC 문장을 그대로 체크리스트 삼아 수동으로
   재현하고 결과를 보고한다. 자동 테스트가 있는 AC는 어떤 테스트 파일이 그것을
   커버하는지 명시할 것 (`/spec-trace` 스킬의 매트릭스를 참고).
5. **결과 보고 형식**: AC 항목을 나열하고 각각 ✅/❌/🟡(부분) + 근거(테스트 이름 또는
   재현 방법)를 붙인다. 전부 ✅가 아니면 다음 Stage로 넘어가지 말라고 명시적으로 말할 것.
6. **완료 확인되면**: `.claude/STAGE`를 다음 번호로 갱신하고, `docs/traceability.md`에
   해당 Stage 절을 추가/갱신한다(`/spec-trace` 절차).

## 주의

이 스킬은 "테스트가 초록불이니 끝났다"로 성급히 결론 내리지 않는다 — `make verify`는
단위 테스트만 돈다. Stage의 AC는 대부분 "실제로 동작하는 경로"(예: Stage 1 AC는 실제
스트리밍 대화가 되는지)를 요구하므로, 인프라가 필요한 AC는 `make dev-up` 후 수동으로
한 번은 직접 실행해보고 보고할 것.
