"""그래프 정적 검증(순환 참조·미도달 노드) 테스트 — FR-AGT-02."""

from agentbuilder.agents.domain import Graph, GraphEdge, GraphNode, NodeType, PromptSpec
from agentbuilder.agents.domain.validation import (
    find_cycles,
    find_unreachable_nodes,
    has_errors,
    lint_graph,
)


def _llm_node(node_id: str) -> GraphNode:
    return GraphNode(id=node_id, type=NodeType.LLM, prompt=PromptSpec(ref=f"{node_id}@v1"))


def _linear_graph() -> Graph:
    return Graph(
        entry="node-a",
        nodes=[_llm_node("node-a"), _llm_node("node-b"), _llm_node("node-c")],
        edges=[
            GraphEdge(**{"from": "node-a", "to": "node-b"}),
            GraphEdge(**{"from": "node-b", "to": "node-c"}),
        ],
    )


def test_linear_graph_has_no_issues() -> None:
    issues = lint_graph(_linear_graph())
    assert issues == []


def test_detects_unreachable_node() -> None:
    graph = Graph(
        entry="node-a",
        nodes=[_llm_node("node-a"), _llm_node("node-b"), _llm_node("orphan-node")],
        edges=[GraphEdge(**{"from": "node-a", "to": "node-b"})],
    )

    unreachable = find_unreachable_nodes(graph)
    assert unreachable == ["orphan-node"]

    issues = lint_graph(graph)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert issues[0].code == "unreachable-node"
    assert not has_errors(issues)


def test_detects_cycle() -> None:
    graph = Graph(
        entry="node-a",
        nodes=[_llm_node("node-a"), _llm_node("node-b"), _llm_node("node-c")],
        edges=[
            GraphEdge(**{"from": "node-a", "to": "node-b"}),
            GraphEdge(**{"from": "node-b", "to": "node-c"}),
            GraphEdge(**{"from": "node-c", "to": "node-a"}),  # node-a로 되돌아감
        ],
    )

    cycles = find_cycles(graph)
    assert len(cycles) == 1
    assert cycles[0][0] == cycles[0][-1] == "node-a"

    issues = lint_graph(graph)
    assert has_errors(issues)
    assert any(i.code == "cyclic-graph" for i in issues)


def test_self_loop_is_a_cycle() -> None:
    graph = Graph(
        entry="node-a",
        nodes=[_llm_node("node-a")],
        edges=[GraphEdge(**{"from": "node-a", "to": "node-a"})],
    )

    assert find_cycles(graph) == [["node-a", "node-a"]]


def test_conditional_branch_both_paths_reachable_no_warning() -> None:
    """분기 구조(risk-assessment 템플릿과 동일 패턴)는 미도달 경고가 없어야 한다."""
    graph = Graph(
        entry="classify",
        nodes=[_llm_node("classify"), _llm_node("high-path"), _llm_node("low-path")],
        edges=[
            GraphEdge(**{"from": "classify", "to": "high-path", "when": "risk == 'high'"}),
            GraphEdge(**{"from": "classify", "to": "low-path", "when": "risk == 'low'"}),
        ],
    )

    assert lint_graph(graph) == []
