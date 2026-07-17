#!/usr/bin/env bash
# SessionStart — dev 스택 상태·브랜치·unit test 결과를 컨텍스트로 주입한다
# (docs/03 §3.2 session-start, 컨텍스트 부트스트랩).
set -uo pipefail
cat >/dev/null # stdin 소비 (사용하지 않음)

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

check_port() {
  timeout 1 bash -c "echo > /dev/tcp/127.0.0.1/$1" 2>/dev/null && echo "up" || echo "down"
}

pg="$(check_port 5432)"
redis="$(check_port 6379)"
qdrant="$(check_port 6333)"

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
dirty="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

# unit 테스트는 외부 의존성이 없고 빠르므로(현재 <1초) 매 세션 시작 시 실행한다.
# 스위트가 커져 느려지면 이 단계를 건너뛰거나 캐시된 결과로 대체할 것.
test_summary="$(uv run pytest tests/unit -q -m "not integration" 2>&1 | tail -1)"

ctx="AgentBuilder 세션 시작.
브랜치: ${branch} (미커밋 변경 ${dirty}건)
로컬 인프라: postgres:${pg} redis:${redis} qdrant:${qdrant} (down이면 로컬 postgresql 서비스를 쓰거나 make dev-up)
unit 테스트: ${test_summary}
작업 규칙: 루트 CLAUDE.md, 진행 단계: docs/03-development-guide.md §5"

jq -n --arg ctx "$ctx" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
