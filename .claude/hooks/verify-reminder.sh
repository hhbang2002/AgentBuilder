#!/usr/bin/env bash
# Stop — 미커밋 .py 변경이 있는데 make verify를 안 돌렸을 수 있으면 경고만 출력한다
# (비차단, docs/03 §3.2 verify-reminder).
set -uo pipefail
cat >/dev/null # stdin 소비 (사용하지 않음)

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

if [[ -n "$(git status --porcelain -- '*.py' 2>/dev/null)" ]]; then
  jq -n '{systemMessage: "변경된 .py 파일이 있습니다 — 커밋 전 `make verify`를 실행했는지 확인하세요."}'
fi
exit 0
