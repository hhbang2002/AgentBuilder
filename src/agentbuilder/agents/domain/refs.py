"""Agent Definition 내 참조 문법(`path@version`) 파싱.

설계문서 §4.2 — "@v3"(불변 버전 고정) / "@stable"(배포 채널 포인터) 두 방식을 지원한다.
이 모듈은 순수 파싱만 담당한다. 실제 참조 해석(DB 조회)은 agents/service의 몫이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_REF_PATTERN = re.compile(r"^(?P<path>[A-Za-z0-9_\-/]+)@(?P<version>v\d+|stable)$")


class InvalidRefError(ValueError):
    """참조 문자열이 `path@version` 형식을 따르지 않을 때."""


@dataclass(frozen=True, slots=True)
class ParsedRef:
    path: str
    """네임스페이스 경로 (예: prompts/ehs-msds-qa, ehs-regulation-qa)."""
    version: str
    """`stable` 또는 `v<N>`."""

    @property
    def is_pinned(self) -> bool:
        return self.version != "stable"

    @property
    def pinned_number(self) -> int | None:
        if not self.is_pinned:
            return None
        return int(self.version[1:])

    def __str__(self) -> str:
        return f"{self.path}@{self.version}"


def parse_ref(ref: str) -> ParsedRef:
    """`"prompts/ehs-msds-qa@v3"` 또는 `"ehs-regulation-qa@stable"`을 파싱한다."""
    m = _REF_PATTERN.match(ref)
    if not m:
        raise InvalidRefError(
            f"올바르지 않은 참조 형식입니다: {ref!r} (예: 'my-prompt@v3' 또는 'my-agent@stable')"
        )
    return ParsedRef(path=m.group("path"), version=m.group("version"))
