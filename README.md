# AgentBuilder — 제조 도메인 특화 Enterprise Agent 플랫폼/Studio

오픈소스 기반으로 **로컬(온프레미스) 환경에서 동작**하는 제조 도메인 특화 AgentBuilder 플랫폼입니다.
모듈식 코어 엔진과 누구나 쉽게 사용할 수 있는 Studio를 제공하여, Enterprise 환경에서
신뢰성 높은 AI 에이전트를 효율적으로 개발·구성·운영할 수 있도록 합니다.

## 핵심 방향 (확정된 설계 결정)

| 항목 | 결정 | 비고 |
|---|---|---|
| LLM 전략 | **하이브리드** | 로컬 LLM(vLLM/Ollama) 우선 + 외부 API(Claude 등) 선택 연결, Model Gateway로 추상화 |
| 오케스트레이션 코어 | **LangGraph + 자체 추상화** | 선언적 Agent 정의 스키마(DSL) → LangGraph로 컴파일 |
| Studio 방식 | **듀얼모드** | 노코드 비주얼 캔버스 + 코드 모드, 선언적 정의(YAML/JSON)가 단일 소스 |
| 도메인 범위 | **품질, 설비/보전, 공정/생산운영, SCM/자재, 안전환경보건(EHS)** | 단계적 롤아웃 |
| 지식 구조화 | **온톨로지 + GraphRAG 연계** | ISA-95 기반 제조 온톨로지, 용어사전, 지식그래프 검색 |
| 배포 형태 | **고객사별 개별 설치 + 배포 설정 팩** | 인증(Keycloak 단독/IdP 연동), 외부 API 정책, 커넥터를 배포별 구성 |
| 언어 | **한국어 + 영어 1급 지원** | Studio UI 포함 (i18n) |
| 개발/파일럿 GPU | **RTX PRO 6000 (96GB)** | 32B급 FP8 / 70B급 4bit 양자화 서빙 기준 |

## 개발 프로세스

```
[1단계] 기능정의  →  [2단계] 설계  →  [3단계] 하네스 엔지니어링 최적화 적용 개발
```

## 문서 체계

| 문서 | 상태 | 설명 |
|---|---|---|
| [docs/01-functional-specification.md](docs/01-functional-specification.md) | ✅ v0.3 확정 | 기능정의서 — EHS 파일럿 확정, 최종 리뷰 보완 반영 |
| [docs/02-architecture-design.md](docs/02-architecture-design.md) | ✅ 최종 리뷰 완료 | 설계문서 — 모듈러 모놀리스 + 포트/어댑터, DSL 명세, ADR 10건 |
| [docs/02b-uiux-design.md](docs/02b-uiux-design.md) | ✅ 작성 완료 | UI/UX 설계 — UX 원칙, IA, 핵심 화면, 사용성 목표(TTFA 30분) |
| [docs/02c-database-design.md](docs/02c-database-design.md) | ✅ 작성 완료 | DB 상세 설계 — 테이블 정의, 인덱스, 파티셔닝, 보존 정책 |
| [docs/03-development-guide.md](docs/03-development-guide.md) | ✅ 작성 완료 | 개발 가이드 — 하네스 엔지니어링(CLAUDE.md/Hooks/Skills/Subagents), 단계별 개발 계획(Stage 0~6) |
