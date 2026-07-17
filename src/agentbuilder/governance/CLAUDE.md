# governance (FR-GOV, FR-OPS)

**책임**: 인증/RBAC, 감사 로그, 가드레일(입력/컨텍스트/출력), 관측성 연동.
**소유 테이블**: `users`, `roles`, `user_roles`, `role_permissions`, `audit.audit_logs`
(insert-only, 해시체인).
**공개 API**: `governance.service`. Keycloak은 `adapters/`에서만 import.

## 현재 구현 상태 (Stage 0)

DB 스키마만 존재(마이그레이션 0001, 0004 시드 역할). 서비스/API 계층 미구현 (Stage 1
인증 최소 구현 → Stage 4 가드레일 정책 팩 대상).

## 자주 하는 실수

- RBAC 검사는 여기 한 곳에만 둘 것 — API 라우터·검색 필터·도구 정책이 각자 권한을
  재구현하면 우회 경로가 생긴다 (ADR-09). 다른 모듈은 `governance.service`의
  `require(resource, action)`류 함수를 호출만 한다
- `guardrails.policyPacks`에서 `org-default`는 해제 불가 — 정책 팩 구현 시 이 제약을
  DSL 검증(`agents/domain`)과 이중으로 지킬 것
- `audit.audit_logs`는 트리거로 UPDATE/DELETE가 막혀 있다 — 정정이 필요하면 정정
  레코드를 새로 추가할 것
