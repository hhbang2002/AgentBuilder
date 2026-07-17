"""seed core data (설계문서 02c §6)

이번 리비전은 02c §6 시드 데이터 목록 중 스키마만으로 의미가 확정되는 두 가지만 다룬다:
표준 6역할(FR-GOV-01), ISA-95 온톨로지 스켈레톤(FR-KNW-04). 나머지 항목(가드레일
정책 팩 본문, 모델 별칭 기본 매핑, EHS 템플릿 임포트)은 해당 값을 실제로 읽고 쓰는
모듈(governance/gateway/deploy 서비스)이 구현되는 단계에서 함께 넣는다 — 소비자
없는 시드는 스키마 드리프트 위험만 키운다.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.sql import column, table

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# 기능정의서 §3 페르소나 ↔ 설계문서 §6.6 RBAC 매핑 — 6개 표준 역할 (FR-GOV-01)
_ROLES: list[tuple[str, str]] = [
    ("platform-admin", "플랫폼 관리자 — 사용자/권한/모델/커넥터/정책 전역 관리"),
    ("agent-developer", "AI 엔지니어 — 코드 모드, 커스텀 노드/도구, 평가 파이프라인 구성"),
    ("domain-editor", "현업 도메인 전문가 — 노코드 캔버스, 템플릿, 지식 검수"),
    ("reviewer", "검토자/승인자 — HITL 승인, 배포 승인, 감사 검토"),
    ("viewer", "뷰어 — 읽기 전용 조회"),
    ("end-user", "최종 사용자 — 배포된 에이전트 소비(챗/API)"),
]

# ISA-95(IEC 62264) 설비 계층 스켈레톤 — code, name_ko, name_en, parent_code
_ISA95_CLASSES: list[tuple[str, str, str, str | None]] = [
    ("isa95.enterprise", "기업", "Enterprise", None),
    ("isa95.site", "사업장", "Site", "isa95.enterprise"),
    ("isa95.area", "구역", "Area", "isa95.site"),
    ("isa95.line", "라인", "Line", "isa95.area"),
    ("isa95.work-cell", "작업셀", "Work Cell", "isa95.line"),
    ("isa95.equipment", "설비", "Equipment", "isa95.work-cell"),
]


def upgrade() -> None:
    roles_t = table(
        "roles",
        column("id", pg.UUID(as_uuid=True)),
        column("name", sa.Text()),
        column("description", sa.Text()),
    )
    role_ids = {name: uuid.uuid4() for name, _ in _ROLES}
    op.bulk_insert(
        roles_t,
        [{"id": role_ids[name], "name": name, "description": desc} for name, desc in _ROLES],
    )

    classes_t = table(
        "ontology_classes",
        column("id", pg.UUID(as_uuid=True)),
        column("code", sa.Text()),
        column("parent_id", pg.UUID(as_uuid=True)),
        column("name_ko", sa.Text()),
        column("name_en", sa.Text()),
        column("source", sa.Text()),
    )
    class_ids: dict[str, uuid.UUID] = {}
    # 부모가 먼저 삽입되어야 하므로 리스트 선언 순서(상위→하위)를 그대로 따른다.
    for code, name_ko, name_en, parent_code in _ISA95_CLASSES:
        class_ids[code] = uuid.uuid4()
        op.bulk_insert(
            classes_t,
            [
                {
                    "id": class_ids[code],
                    "code": code,
                    "parent_id": class_ids[parent_code] if parent_code else None,
                    "name_ko": name_ko,
                    "name_en": name_en,
                    "source": "isa95",
                }
            ],
        )


def downgrade() -> None:
    op.execute("DELETE FROM ontology_classes WHERE source = 'isa95'")
    op.execute(
        "DELETE FROM roles WHERE name IN (" + ", ".join(f"'{name}'" for name, _ in _ROLES) + ")"
    )
