from __future__ import annotations

from pathlib import Path

import pytest

from docsguard.config import ConfigError, load, parse

from .conftest import check, write


def test_defaults_when_there_is_no_config_file(tmp_path: Path) -> None:
    config = load(tmp_path)
    assert config.map_file == "docs/00-READ-FIRST.md" and config.max_lines_per_file == 200


def test_unknown_keys_are_an_error_because_a_typo_must_not_switch_a_guard_off() -> None:
    with pytest.raises(ConfigError, match="unknown key"):
        parse({"max_lines": 100})
    with pytest.raises(ConfigError, match="unknown key"):
        parse({"budget": {"max_line_per_file": 100}})


@pytest.mark.parametrize("bad", [0, -5, "200", True])
def test_budget_values_must_be_positive_integers(bad: object) -> None:
    with pytest.raises(ConfigError, match="positive integer"):
        parse({"budget": {"max_lines_per_file": bad}})


def test_a_dismissal_without_a_written_reason_is_refused() -> None:
    with pytest.raises(ConfigError, match="written reason"):
        parse({"exempt": [{"rule": "map-complete", "path": "docs/x.md", "reason": "tbd"}]})


def test_a_protected_path_must_say_why_it_is_protected() -> None:
    with pytest.raises(ConfigError, match="reason it is protected"):
        parse({"scope": {"protected": [{"pattern": "infra/**", "reason": ""}]}})


def test_invalid_toml_is_reported_with_the_file_name(tmp_path: Path) -> None:
    write(tmp_path, "docsguard.toml", "this is = = not toml")
    with pytest.raises(ConfigError, match=r"docsguard\.toml"):
        load(tmp_path)


def test_an_exemption_removes_exactly_its_finding_and_nothing_else(repo_dir: Path) -> None:
    write(repo_dir, "docs/generated.md", "# Generated\n")
    write(repo_dir, "docs/other.md", "# Other\n")
    assert {f.path for f in check(repo_dir).findings} == {"docs/generated.md", "docs/other.md"}
    with (repo_dir / "docsguard.toml").open("a", encoding="utf-8") as handle:
        handle.write(
            '\n[[exempt]]\nrule = "map-complete"\npath = "docs/generated.md"\n'
            'reason = "generated on every build, not hand-maintained"\n'
        )
    assert {f.path for f in check(repo_dir).findings} == {"docs/other.md"}


def test_an_exemption_that_matches_nothing_is_reported_so_it_cannot_rot(repo_dir: Path) -> None:
    with (repo_dir / "docsguard.toml").open("a", encoding="utf-8") as handle:
        handle.write(
            '\n[[exempt]]\nrule = "map-complete"\npath = "docs/gone.md"\nreason = "was generated once, since deleted"\n'
        )
    stale = [f for f in check(repo_dir).findings if f.rule == "exemptions"]
    assert len(stale) == 1 and "docs/gone.md" in stale[0].message
