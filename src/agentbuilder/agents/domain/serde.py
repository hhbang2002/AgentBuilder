"""Agent Definition의 YAML 직렬화/역직렬화.

설계문서 §4.2 — 정의는 정규화된 YAML로 직렬화되어 Git과 동기화된다 (GitOps, FR-AGT-01).
`sort_keys=False`로 필드 선언 순서를 유지해 Git diff가 사람이 읽기 쉬운 형태가 되도록 한다.
"""

from __future__ import annotations

from typing import Any

import yaml

from agentbuilder.agents.domain.definition import AgentDefinition


class DefinitionParseError(ValueError):
    """YAML 파싱 자체가 실패했을 때 (pydantic ValidationError와 구분)."""


def from_yaml(text: str) -> AgentDefinition:
    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DefinitionParseError(f"YAML 파싱 실패: {exc}") from exc
    if not isinstance(raw, dict):
        raise DefinitionParseError("최상위 문서는 매핑(dict)이어야 합니다")
    return AgentDefinition.model_validate(raw)


def to_yaml(definition: AgentDefinition) -> str:
    return yaml.dump(
        definition.to_dict(),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
