#!/usr/bin/env bash
# PreToolUse(Edit|Write) — deploy/profiles/ 아래에 비밀값으로 보이는 문자열이 쓰이는 것을
# 막는다. 실제 값은 secret_ref(시크릿 저장소 참조)로만 다뤄야 한다. (docs/03 §3.2, FR-DEP-01)
#
# 휴리스틱이다 — PEM 키 블록, 그리고 password/secret/token/api_key 뒤에 오는 비어있지
# 않고 변수 참조($... 아닌)가 아닌 따옴표 문자열을 의심 신호로 본다. 오탐이 있다면
# 이 스크립트를 조정할 것이지, 훅을 끄지 말 것.
set -uo pipefail
input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

if [[ "$file" != *"deploy/profiles/"* ]]; then
  exit 0
fi

content="$(printf '%s' "$input" | jq -r '.tool_input.content // .tool_input.new_string // empty')"

reason=""
if printf '%s' "$content" | grep -Eiq -- '-----BEGIN [A-Z ]*PRIVATE KEY-----'; then
  reason="PEM 개인키 블록으로 보이는 내용이 포함되어 있습니다."
elif printf '%s' "$content" | grep -Eiq '(password|secret|token|api[_-]?key)[[:space:]]*[:=][[:space:]]*"[^"$][^"]{3,}"'; then
  reason="password/secret/token/api_key 뒤에 실제 값으로 보이는 문자열이 포함되어 있습니다."
elif printf '%s' "$content" | grep -Eiq "(password|secret|token|api[_-]?key)[[:space:]]*[:=][[:space:]]*'[^'\$][^']{3,}'"; then
  reason="password/secret/token/api_key 뒤에 실제 값으로 보이는 문자열이 포함되어 있습니다."
fi

if [[ -n "$reason" ]]; then
  jq -n --arg reason "$reason" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("deploy/profiles/ 쓰기가 차단되었습니다 (profile-guard): " + $reason + " secret_ref로 시크릿 저장소를 참조하세요, 값을 직접 쓰지 마세요.")
    }
  }'
  exit 0
fi
exit 0
