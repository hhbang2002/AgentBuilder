"""core platform + agents (설계문서 02c §1, §2.1)

- 공통 트리거 함수 2종: set_updated_at(가변 테이블용), forbid_mutation(불변 버전 테이블용)
  — 02c §1 "불변성" 규약을 애플리케이션 코드가 아닌 DB가 강제한다.
- projects: 02c에 명시적 테이블 정의는 없으나 여러 테이블이 project_id FK로 참조하므로
  워크스페이스 단위 최소 엔티티로 추가 (FR-STD-06 근거).
- deployment_profiles, outbox: 02c §2.6 참조.

Revision ID: 0001
Revises:
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# UUIDv7은 애플리케이션 계층에서 생성해 명시적으로 삽입하는 것을 기본으로 한다
# (시간 정렬 보장은 app 책임). server_default의 gen_random_uuid()는 seed
# 스크립트·수동 SQL 등 app을 거치지 않는 삽입을 위한 v4 폴백일 뿐이다.
_UUID_DEFAULT = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")


def _id_col() -> sa.Column:
    return sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)


def _created_at_col() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def _updated_at_col() -> sa.Column:
    return sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def _attach_updated_at_trigger(table: str, *, schema: str = "public") -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_set_updated_at
        BEFORE UPDATE ON {schema}.{table}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def _make_insert_only(table: str, *, schema: str = "public") -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_forbid_mutation
        BEFORE UPDATE OR DELETE ON {schema}.{table}
        FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
        """
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute(
        "CREATE SCHEMA IF NOT EXISTS checkpoint"
    )  # langgraph-checkpoint-postgres 소유 (Stage 1)

    op.execute(
        """
        CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE FUNCTION forbid_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% is insert-only — % on % 실행이 거부되었습니다 (02c §1 불변성 규약)',
                TG_TABLE_NAME, TG_OP, TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # ── projects ────────────────────────────────────────────────────
    op.create_table(
        "projects",
        _id_col(),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        _created_at_col(),
        _updated_at_col(),
    )
    _attach_updated_at_trigger("projects")

    # ── users / roles / rbac ───────────────────────────────────────
    op.create_table(
        "users",
        _id_col(),
        sa.Column("subject", sa.Text(), nullable=False, unique=True),  # OIDC sub 클레임
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        _created_at_col(),
        _updated_at_col(),
    )
    _attach_updated_at_trigger("users")

    op.create_table(
        "roles",
        _id_col(),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        _created_at_col(),
    )

    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,  # NULL = 전역 역할
        ),
        _created_at_col(),
        sa.PrimaryKeyConstraint("user_id", "role_id", "project_id"),
    )

    op.create_table(
        "role_permissions",
        _id_col(),
        sa.Column(
            "role_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column(
            "scope_project_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    # ── deployment profile / outbox ───────────────────────────────
    op.create_table(
        "deployment_profiles",
        _id_col(),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("config", pg.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )

    op.create_table(
        "outbox",
        _id_col(),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("payload", pg.JSONB(), nullable=False),
        _created_at_col(),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_outbox_unpublished",
        "outbox",
        ["created_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )

    # ── agents / versions / deployments ───────────────────────────
    op.create_table(
        "agents",
        _id_col(),
        sa.Column(
            "project_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("domain_tags", pg.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("owner_team", sa.Text(), nullable=False),
        sa.Column("draft_definition", pg.JSONB(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        _created_at_col(),
        _updated_at_col(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "name", name="uq_agents_project_name"),
    )
    op.create_index(
        "ix_agents_project_active",
        "agents",
        ["project_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    _attach_updated_at_trigger("agents")

    op.create_table(
        "agent_versions",
        _id_col(),
        sa.Column(
            "agent_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", pg.JSONB(), nullable=False),
        sa.Column("definition_hash", sa.Text(), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        _created_at_col(),
        sa.UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
    )
    op.create_index("ix_agent_versions_hash", "agent_versions", ["definition_hash"])
    _make_insert_only("agent_versions")

    op.create_table(
        "deployments",
        _id_col(),
        sa.Column(
            "agent_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("environment", sa.Text(), nullable=False),  # dev | staging | prod
        sa.Column(
            "agent_version_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=True,
        ),
        sa.Column("channel_config", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False, server_default="inactive"),
        _created_at_col(),
        _updated_at_col(),
        sa.UniqueConstraint("agent_id", "environment", name="uq_deployments_agent_environment"),
    )
    _attach_updated_at_trigger("deployments")

    # ── prompt 자산 (FR-STD-04) ────────────────────────────────────
    op.create_table(
        "prompt_templates",
        _id_col(),
        sa.Column(
            "project_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        _created_at_col(),
        sa.UniqueConstraint("project_id", "name", name="uq_prompt_templates_project_name"),
    )

    op.create_table(
        "prompt_versions",
        _id_col(),
        sa.Column(
            "template_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("prompt_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        _created_at_col(),
        sa.UniqueConstraint("template_id", "version", name="uq_prompt_versions_template_version"),
    )
    _make_insert_only("prompt_versions")


def downgrade() -> None:
    op.drop_table("prompt_versions")
    op.drop_table("prompt_templates")
    op.drop_table("deployments")
    op.drop_table("agent_versions")
    op.drop_table("agents")
    op.drop_table("outbox")
    op.drop_table("deployment_profiles")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("projects")
    op.execute("DROP FUNCTION IF EXISTS forbid_mutation() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at() CASCADE")
    op.execute("DROP SCHEMA IF EXISTS checkpoint")
    op.execute("DROP SCHEMA IF EXISTS audit")
