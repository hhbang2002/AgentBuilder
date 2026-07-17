#!/usr/bin/env bash
# PreToolUse(Edit|Write) — migrations/versions/의 기존 리비전 수정을 차단한다.
# 새 리비전 생성(존재하지 않는 파일에 Write)은 허용한다. (docs/03 §3.2 migration-guard)
set -uo pipefail
input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

if [[ "$file" == *"migrations/versions/"*.py && -f "$file" ]]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "기존 마이그레이션 리비전은 수정할 수 없습니다 (docs/03 §3.2 migration-guard, 루트 CLAUDE.md). `make db-migrate m=\"설명\"`으로 새 리비전을 추가하세요."
    }
  }'
  exit 0
fi
exit 0
