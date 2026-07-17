.DEFAULT_GOAL := help
COMPOSE := docker compose -f deploy/compose/dev.yml

.PHONY: help install verify verify-fast fmt lint typecheck imports test test-int \
        dev-up dev-down dev-logs db-migrate db-upgrade db-downgrade db-history

help: ## 사용 가능한 명령 목록
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## 의존성 설치 (uv)
	uv sync

# ── 검증 루프 (docs/03 §3.5) — 사람 = 에이전트 = CI 동일 기준 ─────────
verify: fmt-check lint typecheck imports test ## 전체 검증 (커밋 전 필수, CI와 동일)

verify-fast: ## 변경된 .py 파일만 대상으로 빠르게 검증 (전체 unit test는 그대로 실행)
	@git diff --name-only --diff-filter=ACMR HEAD -- '*.py' > /tmp/ab_changed_files.txt || true
	@if [ -s /tmp/ab_changed_files.txt ]; then \
		echo "변경 파일 대상 ruff/pyright 실행:"; \
		cat /tmp/ab_changed_files.txt; \
		uv run ruff format --check $$(cat /tmp/ab_changed_files.txt) && \
		uv run ruff check $$(cat /tmp/ab_changed_files.txt) && \
		uv run pyright $$(cat /tmp/ab_changed_files.txt); \
	else \
		echo "변경된 .py 파일 없음"; \
	fi
	uv run pytest tests/unit -q

fmt: ## ruff format 적용
	uv run ruff format src tests migrations

fmt-check: ## ruff format 검사만 (미적용 시 실패)
	uv run ruff format --check src tests migrations

lint: ## ruff check
	uv run ruff check src tests migrations

typecheck: ## pyright
	uv run pyright

imports: ## import-linter로 모듈 의존 규칙 검사 (설계문서 §3)
	uv run lint-imports

test: ## 단위 테스트만 (외부 서비스 불필요)
	uv run pytest tests/unit -q -m "not integration"

test-int: ## 통합 테스트 (dev 스택 필요 — 먼저 make dev-up)
	uv run pytest tests/integration -q -m integration

# ── 로컬 개발 스택 ────────────────────────────────────────────────────
dev-up: ## 인프라 서비스 기동 (Postgres/Redis/Qdrant/MinIO/Keycloak/Ollama) + 헬스체크 대기
	$(COMPOSE) up -d
	@echo "postgres/redis 헬스체크 대기 중..."
	@timeout 60 bash -c 'until [ "$$($(COMPOSE) ps postgres --format json | grep -c healthy)" = "1" ] 2>/dev/null; do sleep 2; done' || true
	@echo "qdrant/minio/keycloak/ollama HTTP 응답 대기 중 (최대 90초)..."
	@timeout 90 bash -c 'until curl -sf http://localhost:6333/ >/dev/null; do sleep 2; done' \
		&& echo "  qdrant  ok" || echo "  qdrant  TIMEOUT (이미지가 아직 pull 중일 수 있음 — docker compose logs qdrant 확인)"
	@timeout 90 bash -c 'until curl -sf http://localhost:9000/minio/health/live >/dev/null; do sleep 2; done' \
		&& echo "  minio   ok" || echo "  minio   TIMEOUT"
	@timeout 90 bash -c 'until curl -sf http://localhost:8080/realms/agentbuilder-dev >/dev/null; do sleep 2; done' \
		&& echo "  keycloak ok" || echo "  keycloak TIMEOUT"
	@timeout 90 bash -c 'until curl -sf http://localhost:11434/ >/dev/null; do sleep 2; done' \
		&& echo "  ollama  ok" || echo "  ollama  TIMEOUT"
	@echo "완료. make db-upgrade로 스키마를 적용하세요."

dev-down: ## 인프라 서비스 중지 (볼륨 유지)
	$(COMPOSE) down

dev-down-clean: ## 인프라 서비스 중지 + 볼륨 삭제 (데이터 초기화)
	$(COMPOSE) down -v

dev-logs: ## 인프라 서비스 로그 스트림
	$(COMPOSE) logs -f

# ── DB 마이그레이션 (docs/03 §3.3 /db-migration 스킬과 연동) ──────────
db-migrate: ## 새 마이그레이션 리비전 생성 (예: make db-migrate m="add foo table")
	@test -n "$(m)" || (echo "사용법: make db-migrate m=\"설명\"" && exit 1)
	uv run alembic revision -m "$(m)"

db-upgrade: ## 최신 리비전까지 적용
	uv run alembic upgrade head

db-downgrade: ## 한 단계 되돌리기
	uv run alembic downgrade -1

db-history: ## 마이그레이션 히스토리 출력
	uv run alembic history
