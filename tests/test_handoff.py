from __future__ import annotations

import re
from pathlib import Path

import pytest

from docsguard.rules.handoff import SECTIONS

from .conftest import edit, findings, result

HANDOFF = "docs/HANDOFF.md"


def messages(root: Path) -> list[str]:
    return [f.message for f in findings(root, "handoff-shape")]


def test_the_template_handoff_has_all_eight_sections(repo_dir: Path) -> None:
    assert len(SECTIONS) == 8
    assert result(repo_dir, "handoff-shape").examined == 8 and messages(repo_dir) == []


@pytest.mark.parametrize("index", range(8))
def test_each_missing_section_is_named(repo_dir: Path, index: int) -> None:
    label = SECTIONS[index][0]
    text = (repo_dir / HANDOFF).read_text(encoding="utf-8")
    headings = re.findall(r"^## .*$", text, re.MULTILINE)
    assert len(headings) == 8
    (repo_dir / HANDOFF).write_text(text.replace(headings[index], "## Unrelated heading"), encoding="utf-8")
    assert messages(repo_dir) == [f"is missing the section '{label}'"]


def test_an_empty_section_is_reported_with_its_line(repo_dir: Path) -> None:
    edit(repo_dir, HANDOFF, "Nothing yet.\n\n## 8.", "\n## 8.")
    found = findings(repo_dir, "handoff-shape")
    assert len(found) == 1 and "'learned, not in the code' is empty" in found[0].message and found[0].line


def test_a_missing_or_impossible_date_is_reported(repo_dir: Path) -> None:
    edit(repo_dir, HANDOFF, "Updated:", "Revised:")
    assert any("no 'Updated: YYYY-MM-DD'" in m for m in messages(repo_dir))
    (repo_dir / HANDOFF).write_text(
        (repo_dir / HANDOFF).read_text(encoding="utf-8").replace("Revised:", "Updated:"), encoding="utf-8"
    )
    text = (repo_dir / HANDOFF).read_text(encoding="utf-8")
    (repo_dir / HANDOFF).write_text(
        re.sub(r"Updated: \d{4}-\d{2}-\d{2}", "Updated: 2026-13-45", text), encoding="utf-8"
    )
    assert any("not a real date" in m for m in messages(repo_dir))


def test_a_suite_state_without_a_number_is_expectation_not_measurement(repo_dir: Path) -> None:
    text = (repo_dir / HANDOFF).read_text(encoding="utf-8")
    head, _ = text.split("## 8. Suite state")
    (repo_dir / HANDOFF).write_text(head + "## 8. Suite state\n\nAll green, as expected.\n", encoding="utf-8")
    assert any("carries no number" in m for m in messages(repo_dir))


def test_decisions_must_cite_an_adr_or_say_none(repo_dir: Path) -> None:
    edit(
        repo_dir,
        HANDOFF,
        "- Decisions are recorded as ADRs: [ADR 0001](adr/0001-record-architecture-decisions.md).",
        "- We decided things.",
    )
    assert any("cites no ADR" in m for m in messages(repo_dir))
    edit(repo_dir, HANDOFF, "- We decided things.", "None.")
    assert messages(repo_dir) == []


def test_a_missing_handoff_is_an_error_and_a_disabled_one_is_a_visible_skip(repo_dir: Path) -> None:
    (repo_dir / HANDOFF).unlink()
    assert messages(repo_dir) == ["missing: a fresh session cannot resume from disk alone"]
    (repo_dir / "docsguard.toml").write_text('handoff_file = ""\n', encoding="utf-8")
    outcome = result(repo_dir, "handoff-shape")
    assert outcome.skipped == "handoff disabled in config"
