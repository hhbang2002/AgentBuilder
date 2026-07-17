"""참조 문법(`path@version`) 파싱 테스트."""

import pytest

from agentbuilder.agents.domain import InvalidRefError, parse_ref


def test_parses_pinned_version() -> None:
    ref = parse_ref("prompts/ehs-msds-qa@v3")

    assert ref.path == "prompts/ehs-msds-qa"
    assert ref.version == "v3"
    assert ref.is_pinned is True
    assert ref.pinned_number == 3
    assert str(ref) == "prompts/ehs-msds-qa@v3"


def test_parses_stable_pointer() -> None:
    ref = parse_ref("ehs-regulation-qa@stable")

    assert ref.path == "ehs-regulation-qa"
    assert ref.version == "stable"
    assert ref.is_pinned is False
    assert ref.pinned_number is None


@pytest.mark.parametrize(
    "bad_ref",
    ["no-version-marker", "path@v", "path@latest", "@v1", "path@", "path@v1.2"],
)
def test_rejects_malformed_refs(bad_ref: str) -> None:
    with pytest.raises(InvalidRefError):
        parse_ref(bad_ref)
