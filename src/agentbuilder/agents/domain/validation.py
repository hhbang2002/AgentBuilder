"""Workflow 그래프 정적 검증 (설계문서 §6.1 컴파일 파이프라인 ③ 단계).

`Graph` 생성 시 pydantic 검증기가 이미 구조적 무결성(중복 id·entry 존재·엣지 참조 유효성)을
강제한다. 이 모듈은 그래프 *전체를 순회*해야 판단 가능한 항목 — 순환 참조·미도달 노드 —
을 다룬다. 순수 함수이며 domain 계층에 속한다 (DB·컴파일러 의존 없음).

FR-AGT-02: "순환 참조 검사, 미도달 노드 경고"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentbuilder.agents.domain.definition import Graph

Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    node_id: str | None = None


def _adjacency(graph: Graph) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        adj[edge.from_node].append(edge.to)
    return adj


def find_cycles(graph: Graph) -> list[list[str]]:
    """DFS 기반 사이클 탐지. 발견된 각 사이클을 노드 id 경로로 반환한다."""
    adj = _adjacency(graph)
    color: dict[str, int] = dict.fromkeys(adj, 0)  # 0=white 1=gray 2=black
    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(node: str) -> None:
        color[node] = 1
        path.append(node)
        for nxt in adj[node]:
            if color[nxt] == 1:
                cycle_start = path.index(nxt)
                cycles.append([*path[cycle_start:], nxt])
            elif color[nxt] == 0:
                dfs(nxt)
        path.pop()
        color[node] = 2

    for node_id in adj:
        if color[node_id] == 0:
            dfs(node_id)
    return cycles


def find_unreachable_nodes(graph: Graph) -> list[str]:
    """entry에서 도달할 수 없는 노드 id 목록 (도달 순서 무관, 정렬됨)."""
    adj = _adjacency(graph)
    seen: set[str] = set()
    stack = [graph.entry]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(adj.get(cur, []))
    all_ids = {n.id for n in graph.nodes}
    return sorted(all_ids - seen)


def lint_graph(graph: Graph) -> list[ValidationIssue]:
    """그래프 전체 정적 검증. 순환은 error, 미도달은 warning으로 분류한다."""
    issues: list[ValidationIssue] = []

    for cycle in find_cycles(graph):
        issues.append(
            ValidationIssue(
                severity="error",
                code="cyclic-graph",
                message=f"순환 참조가 발견되었습니다: {' -> '.join(cycle)}",
                node_id=cycle[0],
            )
        )

    for node_id in find_unreachable_nodes(graph):
        issues.append(
            ValidationIssue(
                severity="warning",
                code="unreachable-node",
                message=f"노드 '{node_id}'는 entry('{graph.entry}')에서 도달할 수 없습니다",
                node_id=node_id,
            )
        )

    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(i.severity == "error" for i in issues)
