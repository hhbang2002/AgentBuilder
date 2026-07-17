"""FR-AGT-01: DSL은 JSON Schema 기반 유효성 검증을 지원해야 한다.

이 스키마는 Studio 코드 모드의 자동완성·실시간 검증(설계 §6.7)이 소비한다.
"""

from agentbuilder.agents.domain import AgentDefinition


def test_json_schema_generates_without_error() -> None:
    schema = AgentDefinition.model_json_schema()

    assert schema["title"] == "AgentDefinition"
    assert "properties" in schema
    assert {"apiVersion", "kind", "metadata", "spec"} <= schema["properties"].keys()


def test_json_schema_is_stable_across_calls() -> None:
    """캐싱/비결정 순서로 인한 diff 흔들림 방지 (Git 저장 시 스키마 파일도 함께 버전 관리)."""
    assert AgentDefinition.model_json_schema() == AgentDefinition.model_json_schema()
