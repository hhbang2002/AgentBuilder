# knowledge (FR-KNW)

**책임**: 문서 수집/파싱/청킹/색인 파이프라인, 하이브리드 검색+리랭킹, 온톨로지/용어사전(P1).
**소유 테이블**: `knowledge_spaces`, `documents`, `document_versions`(insert-only), `chunks`,
`ontology_classes`, `ontology_entities`, `glossary_terms`.
**공개 API**: `knowledge.service`. Qdrant·Docling은 `adapters/`에서만 import.

## 현재 구현 상태 (Stage 0)

전 계층 미구현 (Stage 2 대상). Space = Qdrant collection 1:1 (ADR-06) — Space 생성 시
collection도 함께 만들 것.

## 자주 하는 실수

- 문서 삭제를 동기 CASCADE로 처리하지 말 것 — Qdrant point는 PostgreSQL FK로 못 지운다.
  반드시 "삭제 잡"으로 chunks 조회 → Qdrant point 삭제 → chunks 삭제 → MinIO 삭제 순서
  (02c §5, FR-GOV-05)
- 검색 결과는 항상 `RetrievedContext{chunks[], citations[]}` 형태로 반환 — 인용은 생성
  단계가 아니라 검색 단계에서 구조적으로 만든다 (FR-KNW-03)
- 법규 문서(`doc_type='regulation'`)는 `effective_date`/`revision_status` 없이 색인하지
  말 것 (FR-KNW-08)
