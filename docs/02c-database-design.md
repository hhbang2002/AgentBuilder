# AgentBuilder 데이터베이스 상세 설계

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 |
| 상위 문서 | [02-architecture-design.md](02-architecture-design.md) §5 |
| 대상 | PostgreSQL 16+ (메타데이터·체크포인트·감사), Qdrant(벡터), MinIO(오브젝트) |

---

## 1. 설계 규약

| 규약 | 내용 |
|---|---|
| PK | `id UUID` — **UUIDv7** (시간 정렬 → 인덱스 지역성, 분산 생성 가능) |
| 공통 컬럼 | `created_at timestamptz`, `updated_at timestamptz`, `created_by uuid` (감사 최소 단위) |
| 명명 | snake_case, 테이블은 복수형. FK는 `<참조테이블 단수>_id` |
| 삭제 | 사용자 노출 리소스는 소프트 삭제(`deleted_at`) + 유예 후 배치 정리. 파생 데이터(청크·벡터)는 연쇄 하드 삭제 (FR-GOV-05) |
| 불변성 | `*_versions` 테이블은 INSERT-only — UPDATE/DELETE를 트리거로 차단 (감사성 NFR-07) |
| JSONB 사용 기준 | "정의/설정 스냅샷"(스키마가 앱 레벨에서 검증됨)은 JSONB. **조회 조건·조인·집계 대상은 반드시 컬럼으로 승격** |
| 스키마 분리 | `app`(애플리케이션), `checkpoint`(LangGraph 소유 — 라이브러리 마이그레이션 독립), `audit`(감사 — 권한 분리) |
| 마이그레이션 | Alembic. 무중단 원칙: expand → migrate → contract 3단계, 파괴적 DDL은 별도 승인 |

---

## 2. 핵심 테이블 정의

컬럼은 핵심만 기재한다 (전체는 마이그레이션 코드가 진실 원천).

### 2.0 플랫폼 공통 계열 *(v0.2 추가 — Stage 0 구현 리뷰에서 §2 누락 확인, 코드 기준으로 문서 보완)*

```sql
-- 워크스페이스 (FR-STD-06). 다수 테이블이 project_id FK로 참조하는 최소 단위
projects ( id uuid PK, name text UNIQUE, description text )

-- 트랜잭션 커밋과 이벤트 발행의 원자성 보장 (§5 아웃박스 항목, ADR-04)
outbox (
  id uuid PK, topic text, payload jsonb,
  created_at timestamptz, published_at timestamptz NULL   -- NULL = 미발행 (부분 인덱스)
)
```

### 2.1 에이전트/배포 계열

```sql
-- 에이전트 (가변 헤드)
agents (
  id uuid PK, project_id uuid FK, name text UNIQUE(project_id, name),
  display_name text, domain_tags text[], owner_team text,
  draft_definition jsonb,          -- 편집 중 DSL (자동 저장 대상)
  status text,                     -- draft | active | archived
  deleted_at timestamptz
)

-- 불변 버전 스냅샷 (INSERT-only)
agent_versions (
  id uuid PK, agent_id uuid FK, version int UNIQUE(agent_id, version),
  definition jsonb NOT NULL,       -- 참조 해석 완료된 DSL 스냅샷 (프롬프트/도구 버전 고정)
  definition_hash text,            -- 중복 버전 방지 + 재현성 검증
  created_by uuid, created_at timestamptz
)

-- 환경별 배포 포인터
deployments (
  id uuid PK, agent_id uuid FK, environment text,      -- dev | staging | prod
  agent_version_id uuid FK,        -- 현재 서빙 버전 (전환 = 이 포인터 UPDATE + 감사)
  channel_config jsonb,            -- api / web-chat / schedule / event 채널 설정
  status text, UNIQUE(agent_id, environment)
)

prompt_templates ( id, project_id, name UNIQUE(project_id, name), ... )
prompt_versions ( id, template_id FK, version, content text, variables jsonb )  -- INSERT-only
```

### 2.2 지식 계열

```sql
knowledge_spaces (
  id uuid PK, project_id uuid FK, name, data_class text,   -- 데이터 등급 (FR-MDL-02 입력)
  pipeline_config jsonb,           -- 청킹/임베딩 별칭/검색 기본값
  embedding_fingerprint text,      -- 모델 변경 감지 → 재색인 필요 판단 (FR-MDL-03)
  qdrant_collection text UNIQUE    -- Space = collection 1:1 (ADR-06)
)

documents (
  id uuid PK, space_id uuid FK, title, source_uri text,     -- MinIO 키 또는 외부 소스
  content_hash text,               -- 증분 색인 판단
  index_status text,               -- pending | parsing | indexed | failed | review
  index_error jsonb,               -- 실패 단계·사유 (색인 대시보드용)
  access_level text, valid_until date,
  -- 법규 문서 (FR-KNW-08):
  doc_type text,                   -- general | regulation | sop | msds ...
  effective_date date, revision_status text,   -- current | superseded | repealed
  deleted_at timestamptz
)

document_versions ( id, document_id FK, version, source_uri, effective_date, ... ) -- 개정 이력

-- 청크 메타 (벡터·본문 페이로드는 Qdrant, 여기는 관리·연쇄삭제·통계용)
chunks (
  id uuid PK, document_id uuid FK, seq int,
  char_start int, char_end int,    -- v0.2: int4range에서 분리 컬럼으로 변경 (구현 확정 반영)
  qdrant_point_id uuid UNIQUE, token_count int
)

-- 온톨로지 (P1): 스키마/인스턴스 분리
ontology_classes  ( id, code UNIQUE, parent_id FK(self), name_ko, name_en, source text )  -- ISA-95 시드
ontology_entities ( id, class_id FK, code UNIQUE(class_id, code), name, attrs jsonb, parent_id FK(self) )
glossary_terms    ( id, standard_term, synonyms text[], definition, domain_tags text[], status ) -- 검수 워크플로
```

### 2.3 도구/커넥터 계열 (ADR-08 3계층)

```sql
tool_definitions (
  id uuid PK, name UNIQUE, description text,        -- description = LLM이 읽는 사용 설명
  tool_type text,                  -- python | rest | sql | mcp | builtin
  input_schema jsonb, output_schema jsonb,
  default_policy text,             -- auto | approval | deny
  connector_required bool, allowed_roles text[]
)

connector_instances (
  id uuid PK, name UNIQUE, connector_type text,     -- rdb | rest | file | historian | mq
  config jsonb,                    -- 엔드포인트 등 비밀 아닌 설정
  secret_ref text,                 -- 시크릿 저장소 키 (값 저장 금지)
  deployment_profile_id uuid FK, read_only bool DEFAULT true
)

semantic_schemas ( id, connector_instance_id FK, table_name, description, columns jsonb,
                   sample_queries jsonb )            -- Text-to-SQL 시맨틱 레이어 (FR-TOL-04)
```

### 2.4 평가 계열

```sql
datasets      ( id, agent_id FK, name, purpose text )        -- golden | regression | redteam
dataset_items ( id, dataset_id FK, input jsonb, expected jsonb, rubric text,
                meta jsonb,                                   -- 난이도/유형/근거 문서 참조
                source text )                                 -- manual | promoted | synthetic
eval_runs     ( id, agent_version_id FK, dataset_id FK, evaluator_config jsonb,
                status, summary jsonb,                        -- 총점/항목별 집계
                triggered_by text )                           -- manual | gate | ci | monitor
eval_results  ( id, eval_run_id FK, dataset_item_id FK, scores jsonb, passed bool,
                trace_id text )                               -- Langfuse 드릴다운 링크
quality_gates ( id, agent_id FK, environment, dataset_id FK, min_scores jsonb, enabled bool )
```

### 2.5 실행 계열 (대용량 — 파티셔닝 대상)

```sql
threads ( id uuid PK, deployment_id FK, user_id, channel text, meta jsonb )

runs (
  id uuid PK, thread_id FK, agent_version_id FK,
  status text,                     -- queued | running | paused_hitl | done | failed | cancelled
  input jsonb, output jsonb,       -- 대용량 산출물은 MinIO 참조로 절삭
  trace_id text,                   -- Langfuse 연결
  token_usage jsonb, latency_ms int, error jsonb,
  created_at timestamptz           -- 파티션 키
) PARTITION BY RANGE (created_at)  -- 월별

approval_requests (
  id uuid PK, run_id FK, request_type text,          -- tool_execution | deploy_promotion
  payload jsonb,                   -- 요청 요약/근거/영향 (승인함 카드 렌더 소스)
  approver_role text, status text, -- pending | approved | rejected | edited
  decided_by uuid, decided_at timestamptz, decision_note text,
  expires_at timestamptz           -- 만료 정책 (방치 방지)
)

feedback ( id, run_id FK, rating text, reason text, suggested_answer text,
           triage_status text )    -- 피드백→개선 워크플로 (FR-EVL-04)
```

### 2.6 거버넌스 계열

```sql
users ( id, subject UNIQUE,        -- OIDC sub 클레임 (IdP 이관에도 안정)
        email, display_name, status )
roles / user_roles / role_permissions ( resource_type, action, scope_project_id )

audit.audit_logs (
  id uuid PK, occurred_at timestamptz,               -- 파티션 키 (월별)
  actor_id uuid, actor_type text,                    -- user | agent | system
  action text, resource_type text, resource_id uuid,
  detail jsonb, prev_hash text, row_hash text        -- 해시 체인 (변조 감지)
) PARTITION BY RANGE (occurred_at)   -- INSERT-only, 앱 계정에 UPDATE/DELETE 권한 없음

deployment_profiles ( id, name, config jsonb, version, applied_at )  -- 설정 팩 적용 이력
model_usage ( id, occurred_at, project_id, agent_id, model_alias, backend,
              prompt_tokens, completion_tokens, cost_usd, is_external bool )
              PARTITION BY RANGE (occurred_at)       -- 예산·비용 대시보드 집계 원천
```

---

## 3. 인덱스 전략

| 대상 | 인덱스 | 근거 |
|---|---|---|
| 모든 FK | b-tree (자동 아님 — 명시 생성). 유니크 제약/기존 복합 인덱스의 **선두 컬럼**으로 커버되는 FK는 중복 생성하지 않음. 미커버 FK 20건은 리비전 0005에서 일괄 생성 | 조인·연쇄 삭제 (CASCADE 시 자식 순차 스캔 방지) |
| `runs (thread_id, created_at DESC)` | 복합 | 대화 이력 조회 (최빈 쿼리) |
| `runs (status) WHERE status IN ('queued','paused_hitl')` | 부분 인덱스 | 워커 폴링·승인 대기 목록 — 전체 행 대비 극소수 |
| `approval_requests (status, approver_role)` | 복합 부분(`pending`) | 승인함 |
| `documents (space_id, index_status)` | 복합 | 색인 대시보드 |
| `agents (project_id) WHERE deleted_at IS NULL` | 부분 | 카탈로그 목록 |
| `audit_logs (resource_type, resource_id, occurred_at)` | 복합 | 리소스별 감사 추적 |
| `agent_versions (definition_hash)` | b-tree | 중복 버전 감지 |
| JSONB 검색이 필요해지는 필드 | 승격 우선, 불가피하면 GIN | 규약 §1 — GIN 남용 금지 |

---

## 4. 파티셔닝·보존·용량

> **구현 상태 (v0.2)**: 아래 파티션 설계는 목표 상태이며, Stage 0 마이그레이션은
> `runs`/`audit_logs`/`model_usage`를 **일반 테이블로 생성**했다 (0003 리비전 docstring
> 참고 — 스키마 정확성 우선, 데이터가 쌓이기 전 파티션 전환이 더 저렴하다는 판단).
> 파티션 전환 마이그레이션은 **Stage 4(runs 실사용 시작) 착수 전**에 추가한다.

| 테이블 | 파티션 | 보존 정책 (기본값 — 배포 프로파일에서 조정) |
|---|---|---|
| `runs` | 월별 RANGE | 18개월 → 파티션 DROP (요약 통계는 집계 테이블에 보존) |
| `audit.audit_logs` | 월별 RANGE | 5년 (규제 대응) → 아카이브 후 DROP |
| `model_usage` | 월별 RANGE | 원시 13개월, 일별 집계 영구 |
| `eval_results` | 없음(초기) | EvalRun 단위 삭제. 규모 증가 시 파티션 전환 여지 |
| `checkpoint.*` | 라이브러리 기본 | 완료 Run의 체크포인트는 30일 후 정리 잡 (HITL 대기 중은 제외) |

- 보존 삭제는 **파티션 DROP**으로 — 행 단위 DELETE의 vacuum 부하 회피.
- NFR-05 규모(청크 100만) 기준: PostgreSQL 메타데이터는 수 GB 수준 — 병목은 Qdrant 메모리.
  Qdrant는 on-disk payload + 양자화(scalar) 기본 설정으로 단일 노드 커버.

## 5. 무결성·동시성 세부 결정

| 시나리오 | 설계 |
|---|---|
| 버전 승격 경합 | `deployments` 행 `SELECT ... FOR UPDATE` + 버전 포인터 전환은 단일 트랜잭션 (승격 감사 기록 포함) |
| draft 동시 편집 | `agents.draft_definition`에 낙관적 락 (`updated_at` 비교) — 협업 잠금(FR-STD-06)은 P1에 별도 lock 테이블 |
| 큐 잡 멱등성 | 잡 페이로드에 `run_id` — 워커 재시도 시 `runs.status` CAS 갱신으로 중복 실행 방지 |
| 아웃박스 | `outbox (id, topic, payload, published_at NULL)` — 트랜잭션 커밋과 이벤트 발행 원자성 (ADR-04) |
| 감사 해시 체인 | `row_hash = sha256(prev_hash ‖ 정규화 행)` 트리거 계산, 일 1회 앵커 해시 별도 보관 |
| 연쇄 삭제 | 문서 삭제 → chunks 조회 → Qdrant point 삭제 → chunks 삭제 → MinIO 원본 삭제를 **삭제 잡**으로 (동기 FK CASCADE는 Qdrant까지 못 미침 — 잡이 전 구간 보장, FR-GOV-05) |

## 6. 시드 데이터

- `ontology_classes`: ISA-95 계층 스켈레톤 (FR-KNW-04)
- `roles/permissions`: 표준 6역할 매트릭스 (FR-GOV-01)
- 가드레일 정책 팩: `org-default`, `ehs-safety` (FR-GOV-03)
- 모델 별칭 기본 세트: `chat-large / chat-fast / embedding-default / reranker-default`
- EHS 스타터 템플릿 3종 (templates/ehs/ → 설치 시 임포트)
