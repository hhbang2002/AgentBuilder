"""플랫폼 공통 설정 — 환경변수 기반 (pydantic-settings).

os.environ을 직접 읽는 곳은 이 모듈 하나로 제한한다. 다른 모든 코드는 `get_settings()`를
통해서만 설정에 접근한다 — 설정 출처를 한 곳으로 모아 배포 설정 팩(deploy/profiles) 전환을
단순하게 만들기 위함 (설계문서 §9.3).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTBUILDER_", env_file=".env", extra="ignore")

    environment: str = "dev"

    # asyncpg 드라이버 — 런타임 전 구간에서 사용 (Alembic도 async 엔진으로 마이그레이션).
    database_url: str = "postgresql+asyncpg://agentbuilder:agentbuilder@localhost:5432/agentbuilder"
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
