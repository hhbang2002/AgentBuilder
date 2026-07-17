"""Alembic 마이그레이션 실행 환경 — async 엔진 사용 (asyncpg).

DB URL은 platform.adapters.settings.get_settings()에서 가져온다. 마이그레이션 파일
자체는 SQLAlchemy Core(Table/op.create_table)로 작성하므로 이 파일은 ORM MetaData를
바인딩하지 않는다 — target_metadata=None으로 두고 `alembic revision`(자동생성 없이 수동
작성)만 사용한다. 이유: docs/03 §3.2 migration-guard 훅이 기존 리비전 수정을 차단하고,
스키마 변경은 domain Pydantic 모델을 먼저 바꾼 뒤 수동으로 마이그레이션을 작성하는
순서를 강제하기 위함(자동생성은 이 순서를 건너뛰게 만들기 쉽다).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

from agentbuilder.platform.adapters.settings import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(configuration, prefix="sqlalchemy.")

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
