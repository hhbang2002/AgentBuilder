# AgentBuilder 개발 가이드 — 하네스 엔지니어링 & 단계별 개발 계획

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 |
| 상위 문서 | [02-architecture-design.md](02-architecture-design.md) §14 |
| 목적 | AI 코딩 에이전트(Claude Code)로 개발 효율·품질을 극대화하는 하네스 구성과 단계별 개발 계획 정의 |

---

## 1. 하네스 엔지니어링 개요

**하네스 엔지니어링** = AI 코딩 에이전트가 ① 프로젝트 맥락을 즉시 파악하고 ② 스스로
검증하며 ③ 규칙을 벗어나지 못하게 하는 저장소 장치의 집합. 사람 리뷰는 "규칙 위반
잡기"가 아니라 "설계 판단"에 집중하게 된다.

```
CLAUDE.md (맥락)  →  에이전트가 올바른 시작점을 잡는다
Rules (규칙)      →  에이전트가 지켜야 할 경계를 문서가 아닌 도구로 강제한다
Hooks (자동화)    →  포맷·검증·보호를 에이전트 행동에 자동 개입시킨다
Skills (절차)     →  반복 작업(모듈 생성, 마이그레이션 등)을 검증된 절차로 패키징한다
Subagents (분업)  →  탐색·리뷰 등 병렬 가능한 작업을 격리된 컨텍스트로 위임한다
Verify (단일 검증) →  사람·에이전트·CI가 같은 명령으로 같은 기준을 통과한다
```

**원칙**: 문서로 부탁하지 말고 도구로 강제한다. CLAUDE.md에 "~하지 마세요"를 쌓는 대신
lint 규칙·hook·CI 게이트로 만든다. CLAUDE.md는 짧을수록 강하다.

---

## 2. CLAUDE.md 설계

### 2.1 루트 CLAUDE.md (목표: 60줄 이내)

```markdown
# AgentBuilder

제조 도메인 Enterprise Agent 플랫폼. 문서: docs/01(기능정의)·02(설계)·02b(UX)·02c(DB).

## 명령어 (이것만 사용)
- make verify        # lint + typecheck + unit test — 커밋 전 필수, CI와 동일
- make verify-fast   # 변경 파일만
- make test-int      # 통합 테스트 (compose dev 스택 필요: make dev-up)
- make db-migrate m="설명"   # Alembic 마이그레이션 생성 (직접 파일 작성 금지)

## 아키텍처 규칙 (import-linter가 강제 — 위반 시 verify 실패)
- 모듈: platform ← gateway/governance ← agents/knowledge/tools/evals/deploy
- 모듈 간 접근은 상대 모듈의 service/ 공개 API로만
- 외부 라이브러리(langgraph, qdrant_client, litellm, docling)는 adapters/ 안에서만 import
- 스키마 변경은 반드시 domain/ Pydantic 모델 → 마이그레이션 순서로

## 작업 방식
- 새 기능은 tests/ 의 수락 테스트부터 (슬라이스별 AC는 docs/03 §5)
- FR 번호를 커밋 메시지에 표기 (예: feat(knowledge): 하이브리드 검색 RRF [FR-KNW-03])
- 완료 기준: make verify 통과 + 해당 슬라이스 AC 테스트 통과
```

### 2.2 모듈별 CLAUDE.md (각 20줄 이내)

각 `src/agentbuilder/<module>/CLAUDE.md`에: 모듈 책임 1문장, 소유 테이블, 공개
API(service) 목록, 이 모듈에서 자주 틀리는 것 2~3개 (예: knowledge — "청크 삭제 시
Qdrant 연쇄 삭제는 삭제 잡으로, 동기 삭제 금지").

> 유지 규칙: CLAUDE.md 수정은 PR 리뷰 대상. "에이전트가 같은 실수를 2번 하면 규칙 후보,
> 3번 하면 hook/lint 후보"로 승격한다.

---

## 3. Rules / Hooks / Skills / Subagents 구성

### 3.1 Rules (도구로 강제되는 규칙)

| 규칙 | 강제 수단 |
|---|---|
| 모듈 의존 방향 (설계 §3) | **import-linter** contracts — `make verify` 포함 |
| 외부 라이브러리 adapters 격리 | import-linter forbidden 규칙 |
| 코드 스타일·복잡도 | ruff (format+lint), 함수 복잡도 상한 |
| 타입 | pyright strict (domain/·ports/는 100%, adapters/는 basic) |
| 시크릿 커밋 차단 | gitleaks pre-commit + CI |
| 버전 테이블 UPDATE 금지 등 DB 규약 | DB 트리거 (02c §1) + 마이그레이션 리뷰 체크리스트 |
| 프런트 문자열 하드코딩 금지 (i18n) | eslint 규칙 |

### 3.2 Hooks (.claude/settings.json)

| Hook | 시점 | 동작 |
|---|---|---|
| auto-format | PostToolUse (Edit/Write) | 변경 파일에 ruff format / prettier 즉시 적용 — 포맷 지적 왕복 제거 |
| migration-guard | PreToolUse (Edit/Write) | `migrations/versions/` 기존 파일 수정 차단 (새 리비전만 허용) |
| profile-guard | PreToolUse | `deploy/profiles/` 내 `secret` 패턴 포함 쓰기 차단 |
| verify-reminder | Stop | 세션 종료 시 미실행 `make verify` 있으면 경고 출력 |
| session-start | SessionStart | dev 스택 상태·현재 슬라이스·실패 중 테스트 요약 출력 (컨텍스트 부트스트랩) |

### 3.3 Skills (.claude/skills/)

| Skill | 내용 |
|---|---|
| `/new-module-part` | 모듈 표준 구조(domain/ports/adapters/service/api/worker) 스캐폴드 + import-linter 계약 등록 + 테스트 뼈대 |
| `/new-adapter` | 포트 지정 → 어댑터 골격 + 계약 테스트(port conformance test) 생성 — 확장 포인트(설계 §11) 작업 표준화 |
| `/new-node-type` | DSL 노드 타입 추가 절차: 스키마 → 컴파일러 매핑 → 캔버스 팔레트 → 문서, 4곳 동기 수정 체크리스트 |
| `/db-migration` | Pydantic 모델 diff 확인 → Alembic 생성 → expand-contract 검토 질문 → 02c 반영 안내 |
| `/spec-trace` | 구현·테스트에서 FR 커버리지 매트릭스 갱신 (docs/traceability.md) — "기능정의 대비 누락" 자동 점검 |
| `/slice-check` | 현재 슬라이스 AC 테스트 일괄 실행 + 미충족 항목 리포트 |

### 3.4 Subagents (.claude/agents/)

| Subagent | 역할 | 필요 이유 |
|---|---|---|
| `boundary-reviewer` | diff의 모듈 경계·포트 규약·보안(시크릿, SQL 안전장치, 권한 검사 누락) 관점 리뷰 | 본 작업 컨텍스트와 분리된 시선. read-only 도구만 |
| `spec-checker` | 변경이 참조한 FR의 요구사항 문구와 구현·테스트를 대조 | "기능정의 문서 기반 개발"의 상시 검증 |
| `Explore` (내장) | 넓은 코드 탐색 위임 | 메인 컨텍스트 절약 |

> 남용 금지: 서브에이전트는 리뷰·탐색처럼 격리 가치가 있는 곳에만. 구현 자체는 메인
> 세션에서 — 컨텍스트 재구축 비용이 더 크다.

### 3.5 검증 루프 (사람 = 에이전트 = CI 동일 기준)

```
make verify      : ruff + pyright + import-linter + pytest(unit) + eslint/tsc   [< 2분 목표]
make test-int    : compose dev 스택 대상 통합 테스트 (API·큐·DB·Qdrant)          [< 10분]
make test-e2e    : 슬라이스 AC 시나리오 (Playwright 포함)                        [CI nightly]
make eval-regress: 파서/검색 품질 골든셋 회귀 (플랫폼 자체 품질 — 설계 §14-3)     [CI nightly]
```

- CI는 같은 타깃을 실행할 뿐이다. **로컬에서 통과 = CI 통과**를 항상 보장 (환경 차이는
  compose로 고정).
- `verify`가 2분을 넘기 시작하면 하네스 부채로 취급하고 즉시 최적화한다 — 느린 검증은
  에이전트가 검증을 건너뛰게 만든다.

---

## 4. 개발 환경 표준

| 항목 | 선정 |
|---|---|
| Python | 3.12, **uv** (의존성·가상환경), ruff, pyright, pytest(+pytest-asyncio) |
| Frontend | Node 22, pnpm, Vite, TypeScript strict, ESLint+Prettier, Vitest, Playwright |
| 로컬 스택 | `make dev-up` = compose로 PG/Redis/Qdrant/MinIO/Keycloak(dev realm)/Langfuse + **Ollama**(경량 모델 — 개발은 GPU 불필요) |
| 모델 (개발) | Ollama의 소형 모델로 기능 개발, 품질 검증은 연구소 RTX PRO 6000 vLLM 스테이징에서 |
| 브랜치 | trunk-based: `main` + 短命 feature 브랜치, PR 필수, CI 게이트 |

---

## 5. 단계별 개발 계획

수직 슬라이스 원칙(설계 §14): 각 단계는 **동작하는 E2E 경로**를 산출하고, EHS 파일럿
시나리오를 수락 기준(AC)으로 삼는다. 기간은 AI-보조 개발 기준 추정치(±50%)다.

### Stage 0 — 하네스 & 스캐폴드 (1~2주)

| 산출물 | 완료 기준 (DoD) |
|---|---|
| 모노레포 스캐폴드 (설계 §12 구조), 모듈 뼈대 8개 | `make verify` 그린 (빈 프로젝트 기준) |
| 본 문서 §2~4의 하네스 전체 (CLAUDE.md, hooks, skills, subagents, CI) | 신규 세션에서 Claude Code가 지시 없이 verify 루프를 사용함을 확인 |
| compose dev 스택 + Keycloak dev realm | `make dev-up` 후 헬스체크 통과 |
| **도메인 스키마 코드 확정**: DSL Pydantic 모델(설계 §4) + 핵심 테이블 마이그레이션(02c) | 스키마 리뷰 승인 — 이후 모든 작업의 타입 기반 |

### Stage 1 — 코어 실행 경로 (2~3주) — Slice 1

- 범위: DSL 파싱·검증(①~③) → LangGraph 컴파일(`llm` 노드) → agent-worker 실행 →
  RunEvent → SSE 스트리밍. gateway 최소(별칭 해석, Ollama/vLLM, 폴백). threads/runs API.
  dev 인증(Keycloak 토큰 검증만).
- 관련 FR: AGT-01/02/07(부분), MDL-01, OPS-01(트레이스 기록)
- **AC**: `POST /threads/{id}/runs`로 EHS 시스템 프롬프트 에이전트와 스트리밍 대화가
  되고, Langfuse에 트레이스가 남는다. 잘못된 DSL은 위치 명시 오류로 거부된다.

### Stage 2 — 지식 경로 (3주) — Slice 2

- 범위: ingest 파이프라인(PDF/Office, Docling), Space CRUD, Qdrant 하이브리드 검색+RRF,
  리랭커, `retrieval` 노드, 인용 구조 반환, 검색 디버그 API, 증분 색인.
- 관련 FR: KNW-01/02/03, MDL-03
- **AC**: 실제 MSDS·안전절차 PDF 20건을 색인하고, 질의 응답에 **문서/페이지 인용**이
  포함된다. 검색 디버그 API가 단계별 후보·점수를 반환한다. 파싱 실패가 사유와 함께
  기록된다.

### Stage 3 — 도구 & HITL (3주) — Slice 3

- 범위: 도구 레지스트리, python/sql/rest/MCP 실행기, 3계층 커넥터 모델, 도구 정책
  (auto/approval/deny), `hitl-gate`·interrupt·resume, 승인 API, Text-to-SQL 안전장치
  (SELECT 전용·행 제한), 알림(웹훅).
- 관련 FR: TOL-01/02/03(RDB·REST)/04(기본), AGT-05, GOV-02(도구 실행 감사)
- **AC**: "화학물질 마스터 조회(auto)" + "사고 보고 초안 생성(approval)" 시나리오 E2E —
  승인 대기 중 워커 자원이 해제되고, 승인 후 체크포인트에서 재개된다.

### Stage 4 — 평가 & 배포 게이트 (3주) — Slice 4

- 범위: 골든셋 CRUD, evaluator 플러그인(rule + LLM-Judge + Ragas 지표), eval-worker,
  평가 리포트, 버전 스냅샷·환경 승격·품질 게이트·롤백, 웹 챗 채널, 피드백 수집.
- 관련 FR: EVL-01/02/03, STD-05, GOV-03(기본 가드레일 + **ehs-safety 팩 P0**)
- **AC**: 골든셋 30건 기준 미달 버전의 프로덕션 승격이 **차단**되고 리포트에 실패
  케이스가 트레이스 링크와 함께 표시된다. 인용 없는 응답이 가드레일에 걸린다.

### Stage 5 — Studio (4~5주) — Slice 5

- 범위: 카탈로그 홈, 빌더(캔버스+속성패널+코드 토글, ADR-10 동기화), 상주 플레이그라운드
  +실행 인스펙터, 지식 관리 화면(색인 상태·검색 테스트), 평가 리포트 화면, 승인함,
  관리 콘솔(모델 별칭·도구·사용자), RBAC 전면 적용, i18n(ko/en).
- 관련 FR: STD-01/02/03/04/07, GOV-01, 02b 전체
- **AC**: 02b §1의 **TTFA 30분** 시나리오를 비개발자 테스터가 완주. 캔버스↔코드 왕복
  편집에서 정의 드리프트 없음(속성 손실 0). 실행 시각화가 노드 상태를 실시간 반영.

### Stage 6 — MVP 통합 & 파일럿 준비 (2~3주)

- 범위: EHS 스타터 템플릿 3종(01 §8.1), 시드 데이터(02c §6), Compose 패키징·오프라인
  설치 절차, 배포 프로파일 로더, 레드팀 기본 스위트 실행, 부하 테스트(NFR-01/02),
  운영 런북, 파일럿 온보딩 자료.
- **AC**: 깨끗한 GPU 서버에 30분 내 설치 → EHS 템플릿으로 파일럿 시나리오 3종 시연 →
  NFR-01(TTFT p95 ≤ 3s) 측정 통과.

**MVP 합계: 약 18~22주.** 이후 Phase 2(P1)는 기능정의서 §11에 따라 진행하되, 파일럿
피드백으로 우선순위를 재조정한다.

### 병렬화 지침

- Stage 2와 3은 Stage 1 완료 후 **병렬 가능** (knowledge/tools 모듈 독립).
- Studio는 Stage 1 직후 디자인 시스템·레이아웃 셸을 선행 착수 가능 (API 계약은 OpenAPI
  스펙 선공개로 고정).
- 파일럿 골든셋·문서 수집은 **Stage 2부터 현업과 병행** — 개발 완료 후 시작하면 파일럿이
  지연된다 (가장 흔한 실패 패턴).

---

## 6. 요구사항 추적성

- `docs/traceability.md`에 FR ↔ 구현 모듈 ↔ 테스트 ↔ 스테이지 매트릭스를 유지한다
  (`/spec-trace` 스킬이 갱신). MVP 완료 = P0 FR 전체가 "테스트로 검증됨" 상태.
