"""Agent Definition DSL — 플랫폼의 단일 소스 스키마.

설계문서 [02-architecture-design.md] §4 명세를 구현한다. Studio 캔버스·코드 모드·SDK·
Git 저장이 모두 이 스키마를 읽고 쓴다 (FR-AGT-01).

설계 규칙:
- 이 모듈은 순수 도메인 계층이다 — pydantic 외 외부 의존성을 갖지 않는다
  (import-linter 계약 "domain/ports/service는 프레임워크·외부기술 의존 없이 순수").
- 참조(`ref`)는 이 단계에서 해석하지 않는다. 문자열 문법 검증까지만 domain의 책임이고,
  실제 DB 조회는 agents/service가 ports를 통해 수행한다.
- 안전 기본값(fail-safe default) 원칙: 정책류 필드는 "허용"이 아니라 "승인 필요"를
  기본값으로 둔다 (예: ToolBinding.policy 기본값은 approval).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentbuilder.agents.domain.refs import parse_ref

# 식별자(에이전트/노드/스페이스 이름 등)는 API 경로·DB 유니크키·Qdrant collection 이름으로도
# 쓰이므로 kebab-case로 강제한다.
Identifier = Annotated[
    str,
    Field(min_length=2, max_length=63, pattern=r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"),
]


class Kind(StrEnum):
    AGENT = "Agent"
    WORKFLOW = "Workflow"
    SKILL = "Skill"


class DataClass(StrEnum):
    """데이터 민감 등급 (FR-MDL-02, FR-GOV-05) — Model Gateway 라우팅 정책의 입력."""

    PUBLIC = "public"
    INTERNAL = "internal"
    DEPARTMENT = "department"
    CONFIDENTIAL = "confidential"


class ToolPolicy(StrEnum):
    """도구 실행 정책 (FR-AGT-05). 기본값은 항상 APPROVAL — 명시적으로 낮춰야 자동 실행."""

    AUTO = "auto"
    APPROVAL = "approval"
    DENY = "deny"


class CitationMode(StrEnum):
    """RAG 응답의 인용 강제 수준 (FR-KNW-03)."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    NONE = "none"


class NodeType(StrEnum):
    """설계문서 §6.1 '노드 타입 → LangGraph 매핑' 표와 1:1 대응."""

    LLM = "llm"
    AGENT = "agent"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    BRANCH = "branch"
    PARALLEL = "parallel"
    HITL_GATE = "hitl-gate"
    CODE = "code"
    SUBAGENT = "subagent"


class StrictModel(BaseModel):
    """DSL 구성 요소 공통 베이스 — 오타·미지원 필드를 조기에 잡기 위해 extra를 금지한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# ── metadata ──────────────────────────────────────────────────────────


class Metadata(StrictModel):
    name: Identifier
    displayName: str = Field(min_length=1, max_length=200)
    domain: list[str] = Field(default_factory=list)
    owner: str = Field(min_length=1)
    description: str = ""


# ── spec 하위 구성 요소 ───────────────────────────────────────────────


class ModelConfig(StrictModel):
    alias: Identifier
    """실제 모델 매핑은 Model Gateway가 담당한다 (FR-MDL-01) — 여기는 별칭만 참조."""
    params: dict[str, Any] = Field(default_factory=dict)


class SystemPromptRef(StrictModel):
    ref: str
    variables: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_ref_syntax(self) -> Self:
        parse_ref(self.ref)
        return self


class RetrievalConfig(StrictModel):
    topK: int = Field(default=5, gt=0, le=50)
    hybrid: bool = True
    rerank: bool = False
    filters: list[str] = Field(default_factory=list)


class KnowledgeBinding(StrictModel):
    space: Identifier
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


class ToolBinding(StrictModel):
    name: Identifier
    policy: ToolPolicy = ToolPolicy.APPROVAL


class OutputConfig(StrictModel):
    citations: CitationMode = CitationMode.OPTIONAL
    schema_ref: str | None = Field(default=None, alias="schema")

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class GuardrailsConfig(StrictModel):
    policyPacks: list[Identifier] = Field(default_factory=lambda: ["org-default"])

    @model_validator(mode="after")
    def _org_default_always_included(self) -> Self:
        if "org-default" not in self.policyPacks:
            raise ValueError(
                "guardrails.policyPacks에는 'org-default'가 항상 포함되어야 합니다 "
                "(조직 기본 정책은 해제할 수 없습니다 — FR-GOV-03)"
            )
        return self


class ContextBudget(StrictModel):
    history: float = Field(default=0.3, ge=0, le=1)
    knowledge: float = Field(default=0.5, ge=0, le=1)


class RetryConfig(StrictModel):
    """FR-AGT-01 실행 정책의 재시도 요소. LLM 호출·출력 파싱 실패(FR-AGT-07)에 적용된다.

    도구 실행에는 적용되지 않는다 — 도구는 정책(auto/approval/deny) 게이트를 거치며,
    부수효과가 있는 도구를 자동 재시도하면 중복 실행 위험이 있기 때문이다. 도구 실패
    재처리는 에이전트 루프가 에러 컨텍스트를 보고 판단한다 (설계문서 §6.1).
    """

    maxAttempts: int = Field(default=3, ge=1, le=10)
    backoffSeconds: float = Field(default=1.0, ge=0, le=60)


class ExecutionConfig(StrictModel):
    maxSteps: int = Field(default=20, gt=0, le=200)
    timeoutSeconds: int = Field(default=120, gt=0, le=3600)
    contextBudget: ContextBudget = Field(default_factory=ContextBudget)
    retry: RetryConfig = Field(default_factory=RetryConfig)


# ── graph (kind: Workflow) ───────────────────────────────────────────

# 노드 타입별로 필수인 필드. GraphNode._check_required_fields가 검증한다.
_REQUIRED_FIELDS_BY_TYPE: dict[NodeType, tuple[str, ...]] = {
    NodeType.LLM: ("prompt",),
    NodeType.AGENT: ("prompt",),
    NodeType.TOOL: ("tool",),
    NodeType.RETRIEVAL: ("knowledge",),
    NodeType.BRANCH: (),
    NodeType.PARALLEL: ("branches",),
    NodeType.HITL_GATE: ("approvers",),
    NodeType.CODE: ("handler",),
    NodeType.SUBAGENT: ("agent",),
}


class PromptSpec(StrictModel):
    ref: str

    @model_validator(mode="after")
    def _validate_ref_syntax(self) -> Self:
        parse_ref(self.ref)
        return self


class StructuredOutputSpec(StrictModel):
    schema_ref: str = Field(alias="schema")

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class ApproverSpec(StrictModel):
    role: Identifier


class GraphNode(StrictModel):
    id: Identifier
    type: NodeType
    prompt: PromptSpec | None = None
    tool: Identifier | None = None
    agent: str | None = None
    """`subagent` 노드가 참조하는 배포된 에이전트 (예: 'ehs-regulation-qa@stable')."""
    knowledge: list[Identifier] | None = None
    """검색 대상 Knowledge Space 이름 목록 — spec.knowledge에 선언된 것만 참조 가능
    (AgentDefinition._check_graph_references가 교차 검증). 검색 파라미터는 spec.knowledge의
    RetrievalConfig를 그대로 사용한다 (노드별 override는 P2)."""
    output: StructuredOutputSpec | None = None
    approvers: ApproverSpec | None = None
    actions: list[Literal["approve", "reject", "edit"]] | None = None
    branches: list[str] | None = None
    """`parallel` 노드가 fan-out할 하위 노드 id 목록."""
    handler: str | None = None
    """`code` 노드가 로드할 등록된 커스텀 핸들러 식별자."""

    @model_validator(mode="after")
    def _check_required_fields(self) -> Self:
        missing = [f for f in _REQUIRED_FIELDS_BY_TYPE[self.type] if getattr(self, f) is None]
        if missing:
            raise ValueError(
                f"노드 '{self.id}' (type={self.type.value})에 필수 필드가 없습니다: {missing}"
            )
        if self.type == NodeType.SUBAGENT and self.agent is not None:
            parse_ref(self.agent)
        return self


class GraphEdge(StrictModel):
    from_node: Identifier = Field(alias="from")
    to: Identifier
    when: str | None = None
    """CEL 스타일 조건식. None이면 무조건 전이."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Graph(StrictModel):
    entry: Identifier
    nodes: list[GraphNode] = Field(min_length=1)
    edges: list[GraphEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_structural_integrity(self) -> Self:
        ids = [n.id for n in self.nodes]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"노드 id가 중복되었습니다: {sorted(dupes)}")

        id_set = set(ids)
        if self.entry not in id_set:
            raise ValueError(f"entry '{self.entry}'가 nodes에 존재하지 않습니다")

        dangling = [
            (e.from_node, e.to)
            for e in self.edges
            if e.from_node not in id_set or e.to not in id_set
        ]
        if dangling:
            raise ValueError(f"edges가 존재하지 않는 노드를 참조합니다: {dangling}")

        for node in self.nodes:
            if node.type == NodeType.PARALLEL and node.branches:
                unknown = [b for b in node.branches if b not in id_set]
                if unknown:
                    raise ValueError(
                        f"노드 '{node.id}'의 branches가 존재하지 않는 노드를 참조합니다: {unknown}"
                    )
        return self


class AgentSpec(StrictModel):
    model: ModelConfig
    systemPrompt: SystemPromptRef
    knowledge: list[KnowledgeBinding] = Field(default_factory=list)
    tools: list[ToolBinding] = Field(default_factory=list)
    output: OutputConfig = Field(default_factory=OutputConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    dataClass: DataClass = DataClass.INTERNAL
    graph: Graph | None = None
    """kind: Workflow일 때만 설정 — AgentDefinition._check_graph_matches_kind가 강제."""


class AgentDefinition(StrictModel):
    """DSL 최상위 문서. `apiVersion`은 스키마 버전(마이그레이션 단위, FR-AGT-01)."""

    apiVersion: Literal["agentbuilder/v1"] = "agentbuilder/v1"
    kind: Kind
    metadata: Metadata
    spec: AgentSpec

    @model_validator(mode="after")
    def _check_graph_matches_kind(self) -> Self:
        if self.kind == Kind.WORKFLOW and self.spec.graph is None:
            raise ValueError("kind: Workflow는 spec.graph가 필요합니다")
        if self.kind == Kind.AGENT and self.spec.graph is not None:
            raise ValueError(
                "kind: Agent는 spec.graph를 가질 수 없습니다 "
                "(그래프 토폴로지가 필요하면 kind: Workflow를 사용하세요)"
            )
        return self

    @model_validator(mode="after")
    def _check_graph_references_spec(self) -> Self:
        """그래프 노드가 참조하는 도구/지식은 spec에 선언된 것만 허용한다.

        선언 없이 임의 도구를 그래프에서 직접 호출할 수 있다면 실행 정책(policy)이
        정의되지 않은 도구가 실행될 수 있다 — 이를 스키마 단계에서 차단한다.
        """
        if self.spec.graph is None:
            return self

        known_tools = {t.name for t in self.spec.tools}
        known_spaces = {k.space for k in self.spec.knowledge}

        for node in self.spec.graph.nodes:
            if node.type == NodeType.TOOL and node.tool not in known_tools:
                raise ValueError(
                    f"노드 '{node.id}'가 참조하는 도구 '{node.tool}'이 "
                    "spec.tools에 선언되어 있지 않습니다 (실행 정책 미정의)"
                )
            if node.type == NodeType.RETRIEVAL:
                unknown = [s for s in (node.knowledge or []) if s not in known_spaces]
                if unknown:
                    raise ValueError(
                        f"노드 '{node.id}'가 참조하는 Knowledge Space가 "
                        f"spec.knowledge에 선언되어 있지 않습니다: {unknown}"
                    )
        return self

    def to_dict(self) -> dict[str, Any]:
        """정규화된 직렬화 — 필드 선언 순서를 그대로 유지한다 (Git diff 안정성)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
