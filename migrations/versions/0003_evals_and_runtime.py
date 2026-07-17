"""evals + runtime + audit (설계문서 02c §2.4, §2.5, §2.6)

partitioning 참고: 02c §4는 runs/audit_logs/model_usage를 월별 RANGE 파티션으로
설계했다. Stage 0는 스키마 정확성이 우선이므로 일반 테이블로 생성하고, 실 트래픽
규모가 문제되는 시점(로드맵 Phase 2, NFR-05 근거)에 파티션 전환 마이그레이션을
별도로 추가한다 — 데이터가 없는 지금 전환하는 편이 이후보다 훨씬 저렴하다.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_UUID_DEFAULT = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")


def _id_col() -> sa.Column:
    return sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)


def _created_at_col(name: str = "created_at") -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def _attach_updated_at_trigger(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_set_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def upgrade() -> None:
    # ── evals (FR-EVL) ──────────────────────────────────────────────
    op.create_table(
        "datasets",
        _id_col(),
        sa.Column(
            "agent_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "purpose", sa.Text(), nullable=False, server_default="golden"
        ),  # golden|regression|redteam
        _created_at_col(),
        sa.UniqueConstraint("agent_id", "name", name="uq_datasets_agent_name"),
    )

    op.create_table(
        "dataset_items",
        _id_col(),
        sa.Column(
            "dataset_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input", pg.JSONB(), nullable=False),
        sa.Column("expected", pg.JSONB(), nullable=True),
        sa.Column("rubric", sa.Text(), nullable=True),
        sa.Column("meta", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "source", sa.Text(), nullable=False, server_default="manual"
        ),  # manual|promoted|synthetic
    )
    op.create_index("ix_dataset_items_dataset_id", "dataset_items", ["dataset_id"])

    op.create_table(
        "eval_runs",
        _id_col(),
        sa.Column(
            "agent_version_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id", pg.UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False
        ),
        sa.Column("evaluator_config", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("summary", pg.JSONB(), nullable=True),
        sa.Column(
            "triggered_by", sa.Text(), nullable=False, server_default="manual"
        ),  # manual|gate|ci|monitor
        _created_at_col(),
    )
    op.create_index("ix_eval_runs_agent_version_id", "eval_runs", ["agent_version_id"])

    op.create_table(
        "eval_results",
        _id_col(),
        sa.Column(
            "eval_run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_item_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("dataset_items.id"),
            nullable=False,
        ),
        sa.Column("scores", pg.JSONB(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=True),
    )
    op.create_index("ix_eval_results_eval_run_id", "eval_results", ["eval_run_id"])

    op.create_table(
        "quality_gates",
        _id_col(),
        sa.Column(
            "agent_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("environment", sa.Text(), nullable=False),
        sa.Column(
            "dataset_id", pg.UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False
        ),
        sa.Column("min_scores", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("agent_id", "environment", name="uq_quality_gates_agent_environment"),
    )

    # ── runtime (threads/runs/HITL/feedback) ───────────────────────
    op.create_table(
        "threads",
        _id_col(),
        sa.Column(
            "deployment_id", pg.UUID(as_uuid=True), sa.ForeignKey("deployments.id"), nullable=False
        ),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False, server_default="api"),
        sa.Column("meta", pg.JSONB(), nullable=False, server_default="{}"),
        _created_at_col(),
    )
    op.create_index("ix_threads_deployment_id", "threads", ["deployment_id"])

    op.create_table(
        "runs",
        _id_col(),
        sa.Column(
            "thread_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_version_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("input", pg.JSONB(), nullable=True),
        sa.Column("output", pg.JSONB(), nullable=True),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("token_usage", pg.JSONB(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", pg.JSONB(), nullable=True),
        _created_at_col(),
    )
    op.create_index("ix_runs_thread_created", "runs", ["thread_id", sa.text("created_at DESC")])
    op.create_index(
        "ix_runs_active_status",
        "runs",
        ["status"],
        postgresql_where=sa.text("status IN ('queued', 'paused_hitl')"),
    )

    op.create_table(
        "approval_requests",
        _id_col(),
        sa.Column(
            "run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_type", sa.Text(), nullable=False),  # tool_execution | deploy_promotion
        sa.Column("payload", pg.JSONB(), nullable=False),
        sa.Column("approver_role", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("decided_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        _created_at_col(),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_approval_requests_pending",
        "approval_requests",
        ["status", "approver_role"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "feedback",
        _id_col(),
        sa.Column(
            "run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Text(), nullable=False),  # up | down
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("suggested_answer", sa.Text(), nullable=True),
        sa.Column("triage_status", sa.Text(), nullable=False, server_default="new"),
        _created_at_col(),
    )

    # ── audit / usage ──────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        _id_col(),
        _created_at_col("occurred_at"),
        sa.Column("actor_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.Text(), nullable=False),  # user | agent | system
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("detail", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("prev_hash", sa.Text(), nullable=True),
        sa.Column("row_hash", sa.Text(), nullable=True),
        schema="audit",
    )
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id", "occurred_at"],
        schema="audit",
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_forbid_mutation
        BEFORE UPDATE OR DELETE ON audit.audit_logs
        FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
        """
    )

    op.create_table(
        "model_usage",
        _id_col(),
        _created_at_col("occurred_at"),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("agent_id", pg.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("model_alias", sa.Text(), nullable=False),
        sa.Column("backend", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("is_external", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_model_usage_project_occurred", "model_usage", ["project_id", "occurred_at"])


def downgrade() -> None:
    op.drop_table("model_usage")
    op.drop_table("audit_logs", schema="audit")
    op.drop_table("feedback")
    op.drop_table("approval_requests")
    op.drop_table("runs")
    op.drop_table("threads")
    op.drop_table("quality_gates")
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("dataset_items")
    op.drop_table("datasets")
