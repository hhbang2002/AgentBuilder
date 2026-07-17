"""FK 인덱스 보강 (설계문서 02c §3 "모든 FK: b-tree 명시 생성" 이행)

Stage 0 리뷰(spec-checker)에서 발견된 미이행 항목. 유니크 제약/기존 인덱스의 선두
컬럼으로 이미 커버되는 FK는 제외하고, 명시 인덱스가 없던 FK 컬럼만 추가한다.
CASCADE 삭제 경로의 자식 테이블 FK는 인덱스가 없으면 부모 행 삭제 시 순차 스캔이
발생하므로(PostgreSQL은 FK에 자동 인덱스를 만들지 않음) 특히 중요하다.

audit.audit_logs.actor_id는 FK 제약이 없는 일반 컬럼이지만(감사 스키마의 의도적
비결합) 행위자 기준 감사 조회(FR-GOV-02)를 위해 함께 인덱싱한다.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# (인덱스명, 테이블, 컬럼, 스키마)
_INDEXES: list[tuple[str, str, str, str | None]] = [
    ("ix_agents_created_by", "agents", "created_by", None),
    ("ix_agent_versions_created_by", "agent_versions", "created_by", None),
    ("ix_prompt_versions_created_by", "prompt_versions", "created_by", None),
    ("ix_deployments_agent_version_id", "deployments", "agent_version_id", None),
    ("ix_ontology_classes_parent_id", "ontology_classes", "parent_id", None),
    ("ix_ontology_entities_parent_id", "ontology_entities", "parent_id", None),
    ("ix_connector_instances_profile_id", "connector_instances", "deployment_profile_id", None),
    ("ix_semantic_schemas_connector_id", "semantic_schemas", "connector_instance_id", None),
    ("ix_eval_runs_dataset_id", "eval_runs", "dataset_id", None),
    ("ix_eval_results_dataset_item_id", "eval_results", "dataset_item_id", None),
    ("ix_quality_gates_dataset_id", "quality_gates", "dataset_id", None),
    ("ix_threads_user_id", "threads", "user_id", None),
    ("ix_runs_agent_version_id", "runs", "agent_version_id", None),
    ("ix_approval_requests_run_id", "approval_requests", "run_id", None),
    ("ix_approval_requests_decided_by", "approval_requests", "decided_by", None),
    ("ix_feedback_run_id", "feedback", "run_id", None),
    ("ix_model_usage_agent_id", "model_usage", "agent_id", None),
    ("ix_user_roles_role_id", "user_roles", "role_id", None),
    ("ix_role_permissions_scope_project_id", "role_permissions", "scope_project_id", None),
    ("ix_audit_logs_actor_id", "audit_logs", "actor_id", "audit"),
]


def upgrade() -> None:
    for name, table, column, schema in _INDEXES:
        op.create_index(name, table, [column], schema=schema)


def downgrade() -> None:
    for name, table, _column, schema in reversed(_INDEXES):
        op.drop_index(name, table_name=table, schema=schema)
