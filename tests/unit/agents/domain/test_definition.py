"""Agent Definition DSL 도메인 모델 테스트.

templates/ehs/*.yaml (실제 EHS 파일럿 스타터 템플릿)을 정본 픽스처로 사용한다 —
문서(설계 §4.1)·템플릿·테스트가 항상 같은 예시를 가리키게 하기 위함.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from agentbuilder.agents.domain import (
    AgentDefinition,
    DataClass,
    Kind,
    NodeType,
    ToolPolicy,
    from_yaml,
    to_yaml,
)

TEMPLATES_DIR = Path(__file__).parents[4] / "templates" / "ehs"


def _load(filename: str) -> AgentDefinition:
    return from_yaml((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))


class TestAgentKind:
    def test_msds_qa_template_parses(self) -> None:
        definition = _load("msds-qa.agent.yaml")

        assert definition.kind == Kind.AGENT
        assert definition.metadata.name == "ehs-msds-qa"
        assert definition.spec.model.alias == "chat-large"
        assert definition.spec.dataClass == DataClass.INTERNAL
        assert definition.spec.graph is None

    def test_tool_default_policy_is_approval_not_auto(self) -> None:
        """안전 기본값 원칙: policy를 명시하지 않으면 자동 실행되어서는 안 된다."""
        definition = _load("msds-qa.agent.yaml")
        by_name = {t.name: t.policy for t in definition.spec.tools}

        assert by_name["chemical-master-lookup"] == ToolPolicy.AUTO  # 명시적으로 auto
        assert by_name["incident-report-create"] == ToolPolicy.APPROVAL

    def test_org_default_guardrail_pack_is_mandatory(self) -> None:
        raw = (TEMPLATES_DIR / "msds-qa.agent.yaml").read_text(encoding="utf-8")
        broken = raw.replace("policyPacks: [org-default, ehs-safety]", "policyPacks: [ehs-safety]")
        with pytest.raises(ValidationError, match="org-default"):
            from_yaml(broken)

    def test_agent_kind_cannot_declare_graph(self) -> None:
        raw = (TEMPLATES_DIR / "msds-qa.agent.yaml").read_text(encoding="utf-8")
        raw += (
            "\n  graph:\n    entry: step-a\n"
            "    nodes: [{id: step-a, type: llm, prompt: {ref: some-prompt@v1}}]\n"
        )
        with pytest.raises(ValidationError, match="kind: Agent"):
            from_yaml(raw)


class TestWorkflowKind:
    def test_risk_assessment_template_parses(self) -> None:
        definition = _load("risk-assessment.workflow.yaml")

        assert definition.kind == Kind.WORKFLOW
        assert definition.spec.graph is not None
        assert definition.spec.graph.entry == "classify"
        assert {n.id for n in definition.spec.graph.nodes} == {
            "classify",
            "assess",
            "approve",
            "report",
        }

    def test_workflow_kind_requires_graph(self) -> None:
        raw = (TEMPLATES_DIR / "risk-assessment.workflow.yaml").read_text(encoding="utf-8")
        without_graph = raw.split("\n  graph:")[0] + "\n"
        with pytest.raises(ValidationError, match="kind: Workflow"):
            from_yaml(without_graph)

    def test_node_referencing_undeclared_tool_is_rejected(self) -> None:
        raw = (TEMPLATES_DIR / "risk-assessment.workflow.yaml").read_text(encoding="utf-8")
        broken = raw.replace("tool: risk-assessment-doc-create", "tool: undeclared-tool")
        with pytest.raises(ValidationError, match="undeclared-tool"):
            from_yaml(broken)

    def test_duplicate_node_id_is_rejected(self) -> None:
        raw = (TEMPLATES_DIR / "risk-assessment.workflow.yaml").read_text(encoding="utf-8")
        broken = raw.replace("id: report", "id: classify", 1)
        with pytest.raises(ValidationError, match="중복"):
            from_yaml(broken)

    def test_dangling_edge_reference_is_rejected(self) -> None:
        raw = (TEMPLATES_DIR / "risk-assessment.workflow.yaml").read_text(encoding="utf-8")
        broken = raw.replace(
            "{ from: approve, to: report, when: \"action == 'approve'\" }",
            "{ from: approve, to: nonexistent }",
        )
        with pytest.raises(ValidationError, match="존재하지 않는 노드"):
            from_yaml(broken)

    def test_hitl_gate_missing_approvers_is_rejected(self) -> None:
        raw = (TEMPLATES_DIR / "risk-assessment.workflow.yaml").read_text(encoding="utf-8")
        broken = raw.replace("        approvers: { role: ehs-manager }\n", "")
        with pytest.raises(ValidationError, match="approvers"):
            from_yaml(broken)


class TestNodeType:
    def test_all_node_types_have_required_field_rules(self) -> None:
        from agentbuilder.agents.domain.definition import _REQUIRED_FIELDS_BY_TYPE

        assert set(_REQUIRED_FIELDS_BY_TYPE) == set(NodeType)


class TestSerde:
    def test_round_trip_preserves_semantics(self) -> None:
        original = _load("risk-assessment.workflow.yaml")
        round_tripped = from_yaml(to_yaml(original))

        assert round_tripped == original

    def test_to_yaml_preserves_field_order(self) -> None:
        definition = _load("msds-qa.agent.yaml")
        rendered = to_yaml(definition)

        assert rendered.index("apiVersion") < rendered.index("kind")
        assert rendered.index("kind") < rendered.index("metadata")
        assert rendered.index("metadata") < rendered.index("spec")


class TestIdentifierValidation:
    @pytest.mark.parametrize("bad_name", ["Ehs-Msds", "ehs_msds", "1ehs", "e", "ehs--msds"])
    def test_rejects_non_kebab_case_names(self, bad_name: str) -> None:
        raw = (TEMPLATES_DIR / "msds-qa.agent.yaml").read_text(encoding="utf-8")
        broken = raw.replace("name: ehs-msds-qa", f"name: {bad_name}")
        with pytest.raises(ValidationError):
            from_yaml(broken)
