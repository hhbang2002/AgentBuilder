#!/usr/bin/env bash
# PostToolUse(Edit|Write) — 변경된 .py 파일에 ruff format 자동 적용 (docs/03 §3.2).
set -uo pipefail
input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')"

if [[ "$file" == *.py && -f "$file" ]]; then
  uv run ruff format "$file" >/dev/null 2>&1 || true
fi
exit 0
