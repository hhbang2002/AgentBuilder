"""knowledge + tools (설계문서 02c §2.2, §2.3)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_UUID_DEFAULT = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")


def _id_col() -> sa.Column:
    return sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)


def _created_at_col() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def _updated_at_col() -> sa.Column:
    return sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW)


def _attach_updated_at_trigger(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_set_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def _make_insert_only(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_forbid_mutation
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
        """
    )


def upgrade() -> None:
    # ── knowledge ───────────────────────────────────────────────────
    op.create_table(
        "knowledge_spaces",
        _id_col(),
        sa.Column(
            "project_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("data_class", sa.Text(), nullable=False, server_default="internal"),
        sa.Column("pipeline_config", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("embedding_fingerprint", sa.Text(), nullable=True),
        sa.Column("qdrant_collection", sa.Text(), nullable=False, unique=True),
        _created_at_col(),
        _updated_at_col(),
        sa.UniqueConstraint("project_id", "name", name="uq_knowledge_spaces_project_name"),
    )
    _attach_updated_at_trigger("knowledge_spaces")

    op.create_table(
        "documents",
        _id_col(),
        sa.Column(
            "space_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("index_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("index_error", pg.JSONB(), nullable=True),
        sa.Column("access_level", sa.Text(), nullable=False, server_default="internal"),
        sa.Column("valid_until", sa.Date(), nullable=True),
        # 법규 문서 (FR-KNW-08):
        sa.Column("doc_type", sa.Text(), nullable=False, server_default="general"),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("revision_status", sa.Text(), nullable=False, server_default="current"),
        _created_at_col(),
        _updated_at_col(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_space_status", "documents", ["space_id", "index_status"])
    _attach_updated_at_trigger("documents")

    op.create_table(
        "document_versions",
        _id_col(),
        sa.Column(
            "document_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        _created_at_col(),
        sa.UniqueConstraint("document_id", "version", name="uq_document_versions_document_version"),
    )
    _make_insert_only("document_versions")

    op.create_table(
        "chunks",
        _id_col(),
        sa.Column(
            "document_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("qdrant_point_id", pg.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    # ── ontology / glossary (FR-KNW-04/05, P1) ────────────────────
    op.create_table(
        "ontology_classes",
        _id_col(),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "parent_id", pg.UUID(as_uuid=True), sa.ForeignKey("ontology_classes.id"), nullable=True
        ),
        sa.Column("name_ko", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="custom"),  # isa95 | custom
    )

    op.create_table(
        "ontology_entities",
        _id_col(),
        sa.Column(
            "class_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("ontology_classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("attrs", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "parent_id", pg.UUID(as_uuid=True), sa.ForeignKey("ontology_entities.id"), nullable=True
        ),
        sa.UniqueConstraint("class_id", "code", name="uq_ontology_entities_class_code"),
    )

    op.create_table(
        "glossary_terms",
        _id_col(),
        sa.Column("standard_term", sa.Text(), nullable=False),
        sa.Column("synonyms", pg.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("definition", sa.Text(), nullable=False, server_default=""),
        sa.Column("domain_tags", pg.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),  # draft | approved
    )

    # ── tools / connectors (FR-TOL, ADR-08 3계층) ─────────────────
    op.create_table(
        "tool_definitions",
        _id_col(),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tool_type", sa.Text(), nullable=False),  # python | rest | sql | mcp | builtin
        sa.Column("input_schema", pg.JSONB(), nullable=False),
        sa.Column("output_schema", pg.JSONB(), nullable=False),
        sa.Column("default_policy", sa.Text(), nullable=False, server_default="approval"),
        sa.Column("connector_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowed_roles", pg.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        _created_at_col(),
        _updated_at_col(),
    )
    _attach_updated_at_trigger("tool_definitions")

    op.create_table(
        "connector_instances",
        _id_col(),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "connector_type", sa.Text(), nullable=False
        ),  # rdb | rest | file | historian | mq
        sa.Column("config", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("secret_ref", sa.Text(), nullable=True),
        sa.Column(
            "deployment_profile_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("deployment_profiles.id"),
            nullable=True,
        ),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created_at_col(),
        _updated_at_col(),
    )
    _attach_updated_at_trigger("connector_instances")

    op.create_table(
        "semantic_schemas",
        _id_col(),
        sa.Column(
            "connector_instance_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("connector_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("columns", pg.JSONB(), nullable=False, server_default="[]"),
        sa.Column("sample_queries", pg.JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_table("semantic_schemas")
    op.drop_table("connector_instances")
    op.drop_table("tool_definitions")
    op.drop_table("glossary_terms")
    op.drop_table("ontology_entities")
    op.drop_table("ontology_classes")
    op.drop_table("chunks")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("knowledge_spaces")
