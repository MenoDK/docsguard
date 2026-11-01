from __future__ import annotations

from pathlib import Path

from docsguard.rules.adr import STATUSES

from .conftest import edit, findings, result, write

GOOD = """# 0002. Use Postgres

Status: Accepted

## Context

We need transactions across two tables.

## Decision

Use Postgres.

## Rejected alternatives

- **A document store.** No multi-document transactions at the time of writing.
"""


def add_adr(root: Path, name: str = "0002-use-postgres.md", text: str = GOOD, index: bool = True) -> None:
    write(root, f"docs/adr/{name}", text)
    if index:
        with (root / "docs/adr/README.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\n| [x]({name}) | y |\n")


def messages(root: Path) -> list[str]:
    return [f.message for f in findings(root, "adr-shape")]


def test_a_complete_record_passes(repo_dir: Path) -> None:
    add_adr(repo_dir)
    assert findings(repo_dir, "adr-shape") == []
    assert result(repo_dir, "adr-shape").examined == 2


def test_an_adr_with_no_rejected_alternatives_is_a_changelog_entry_and_fails(repo_dir: Path) -> None:
    add_adr(repo_dir, text=GOOD.split("## Rejected")[0])
    assert any("Rejected alternatives" in m for m in messages(repo_dir))


def test_a_rejected_section_that_names_nothing_fails(repo_dir: Path) -> None:
    add_adr(
        repo_dir,
        text=GOOD.replace("- **A document store.** No multi-document transactions at the time of writing.", "tbd"),
    )
    assert any("names no alternative" in m for m in messages(repo_dir))


def test_empty_context_and_decision_are_reported_separately(repo_dir: Path) -> None:
    add_adr(repo_dir, text=GOOD.replace("We need transactions across two tables.", "").replace("Use Postgres.", ""))
    found = messages(repo_dir)
    assert any("'## Context' is empty" in m for m in found)
    assert any("'## Decision' is empty" in m for m in found)


def test_a_missing_status_or_an_unknown_one_is_reported(repo_dir: Path) -> None:
    add_adr(repo_dir, text=GOOD.replace("Status: Accepted\n", ""))
    assert any("no 'Status:' line" in m for m in messages(repo_dir))
    edit(repo_dir, "docs/adr/0002-use-postgres.md", "# 0002. Use Postgres\n", "# 0002. Use Postgres\n\nStatus: Maybe\n")
    assert any("no 'Status:' line" in m for m in messages(repo_dir))
    assert set(STATUSES) >= {"Accepted", "Superseded"}


def test_markdown_bold_status_is_accepted(repo_dir: Path) -> None:
    add_adr(repo_dir, text=GOOD.replace("Status: Accepted", "**Status:** Accepted"))
    assert findings(repo_dir, "adr-shape") == []


def test_a_record_without_a_title_is_reported(repo_dir: Path) -> None:
    add_adr(repo_dir, text=GOOD.replace("# 0002. Use Postgres\n", ""))
    assert any("no '# Title'" in m for m in messages(repo_dir))


def test_a_gap_in_numbering_names_the_missing_number(repo_dir: Path) -> None:
    add_adr(repo_dir, name="0003-skipped-two.md", text=GOOD)
    assert any("0002 is missing" in m for m in messages(repo_dir))


def test_a_duplicate_number_is_reported_on_the_second_file(repo_dir: Path) -> None:
    add_adr(
        repo_dir, name="0001-zz-duplicate.md", text=GOOD
    )  # sorts after the template's 0001: the later file is accused
    found = findings(repo_dir, "adr-shape")
    assert [f.path for f in found if "already used" in f.message] == ["docs/adr/0001-zz-duplicate.md"]


def test_a_record_missing_from_the_index_is_reported_by_name(repo_dir: Path) -> None:
    add_adr(repo_dir, index=False)
    found = findings(repo_dir, "adr-shape")
    assert [f.path for f in found if "not listed" in f.message] == ["docs/adr/0002-use-postgres.md"]


def test_a_bad_file_name_is_reported(repo_dir: Path) -> None:
    add_adr(repo_dir, name="use-postgres.md", index=False)
    assert any("0007-short-kebab-title.md" in m for m in messages(repo_dir))


def test_superseded_must_name_an_adr_that_exists(repo_dir: Path) -> None:
    add_adr(repo_dir, text=GOOD.replace("Status: Accepted", "Status: Superseded"))
    assert any("does not say by which ADR" in m for m in messages(repo_dir))
    edit(repo_dir, "docs/adr/0002-use-postgres.md", "Status: Superseded", "Status: Superseded by ADR-0009")
    assert any("0009, which does not exist" in m for m in messages(repo_dir))
    edit(repo_dir, "docs/adr/0002-use-postgres.md", "Superseded by ADR-0009", "Superseded by ADR-0001")
    assert findings(repo_dir, "adr-shape") == []


def test_no_adr_directory_is_an_explicit_skip(repo_dir: Path) -> None:
    for path in sorted((repo_dir / "docs/adr").iterdir()):
        path.unlink()
    (repo_dir / "docs/adr").rmdir()
    outcome = result(repo_dir, "adr-shape")
    assert outcome.skipped and outcome.ok


def test_a_missing_index_is_reported(repo_dir: Path) -> None:
    (repo_dir / "docs/adr/README.md").unlink()
    assert any("index is missing" in m for m in messages(repo_dir))
