from __future__ import annotations

from pathlib import Path

from docsguard.rules.docs_map import INDEX_NAMES

from .conftest import check, edit, findings, result, write


def test_a_document_missing_from_the_map_is_accused_by_name(repo_dir: Path) -> None:
    write(repo_dir, "docs/runbook.md", "# Runbook\n")
    found = findings(repo_dir, "map-complete")
    assert [f.path for f in found] == ["docs/runbook.md"]
    assert "same commit" in found[0].message


def test_adding_it_to_the_map_fixes_it(repo_dir: Path) -> None:
    write(repo_dir, "docs/runbook.md", "# Runbook\n")
    edit(
        repo_dir,
        "docs/00-READ-FIRST.md",
        "| must coordinate",
        "| operate it | [Runbook](runbook.md) |\n| must coordinate",
    )
    assert findings(repo_dir, "map-complete") == []


def test_a_document_listed_in_a_mapped_index_counts_as_mapped(repo_dir: Path) -> None:
    write(repo_dir, "docs/knowledge-tree/second.md", "# Second\n")
    assert [f.path for f in findings(repo_dir, "map-complete")] == ["docs/knowledge-tree/second.md"]
    edit(
        repo_dir,
        "docs/knowledge-tree/README.md",
        "| [Example branch]",
        "| [Second](second.md) | more |\n| [Example branch]",
    )
    assert findings(repo_dir, "map-complete") == []


def test_only_index_files_fan_out_so_a_plain_document_cannot_launder_an_orphan(repo_dir: Path) -> None:
    # B is linked only from A, and A is a normal document: B is still not "mapped".
    write(repo_dir, "docs/a.md", "# A\n[B](b.md)\n")
    write(repo_dir, "docs/b.md", "# B\n")
    edit(repo_dir, "docs/00-READ-FIRST.md", "| must coordinate", "| read a | [A](a.md) |\n| must coordinate")
    assert [f.path for f in findings(repo_dir, "map-complete")] == ["docs/b.md"]
    assert "README.md" in INDEX_NAMES


def test_archived_documents_are_not_expected_in_the_map(repo_dir: Path) -> None:
    write(repo_dir, "docs/archive/old-plan.md", "# Old plan\n")
    assert findings(repo_dir, "map-complete") == []


def test_a_dead_link_in_the_map_is_reported_with_its_line(repo_dir: Path) -> None:
    edit(repo_dir, "docs/00-READ-FIRST.md", "(CHECKLIST.md)", "(CHECKLIST-RENAMED.md)")
    found = findings(repo_dir, "map-links-live")
    assert len(found) == 1
    assert found[0].path == "docs/00-READ-FIRST.md"
    assert found[0].line is not None
    assert "CHECKLIST-RENAMED.md" in found[0].message


def test_external_links_and_anchors_are_not_checked_as_files(repo_dir: Path) -> None:
    with (repo_dir / "docs" / "00-READ-FIRST.md").open("a", encoding="utf-8") as handle:
        handle.write("\n[site](https://example.com) [top](#read-first) [mail](mailto:a@example.test)\n")
    assert findings(repo_dir, "map-links-live") == []


def test_links_inside_code_fences_and_inline_code_are_examples_not_links(repo_dir: Path) -> None:
    with (repo_dir / "docs" / "00-READ-FIRST.md").open("a", encoding="utf-8") as handle:
        handle.write("\n`[x](nowhere.md)`\n\n```\n[y](also-nowhere.md)\n```\n")
    assert findings(repo_dir, "map-links-live") == []


def test_a_count_the_map_declares_is_verified_against_the_disk(repo_dir: Path) -> None:
    write(repo_dir, "docs/adr/0002-second.md", "# 0002\n")
    found = findings(repo_dir, "map-counts")
    assert len(found) == 1
    assert "declares 1" in found[0].message and "has 2" in found[0].message


def test_a_malformed_count_marker_is_an_error_not_a_pass(repo_dir: Path) -> None:
    edit(repo_dir, "docs/00-READ-FIRST.md", "expect=1", "expect=many")
    found = findings(repo_dir, "map-counts")
    assert len(found) == 1 and "numeric expect" in found[0].message


def test_a_map_with_no_counts_is_skipped_explicitly_not_passed(repo_dir: Path) -> None:
    edit(repo_dir, "docs/00-READ-FIRST.md", " <!-- docsguard:count dir=docs/adr glob=0*.md expect=1 -->", "")
    outcome = result(repo_dir, "map-counts")
    assert outcome.skipped and outcome.examined == 0 and outcome.ok


def test_a_missing_map_fails_every_map_rule(repo_dir: Path) -> None:
    (repo_dir / "docs" / "00-READ-FIRST.md").unlink()
    for rule in ("map-links-live", "map-complete", "map-counts"):
        assert [f.message for f in findings(repo_dir, rule)] == ["the docs map does not exist"]


def test_claude_md_must_exist_and_point_at_the_map(repo_dir: Path) -> None:
    write(repo_dir, "CLAUDE.md", "# demo\n\nNo pointer to anything.\n")
    assert "does not point at the docs map" in findings(repo_dir, "claude-entrypoint")[0].message
    (repo_dir / "CLAUDE.md").unlink()
    assert "missing" in findings(repo_dir, "claude-entrypoint")[0].message


def test_a_map_whose_links_are_all_external_examined_nothing_and_fails(repo_dir: Path) -> None:
    write(repo_dir, "docs/00-READ-FIRST.md", "# Map\n[x](https://example.com)\n")
    outcome = result(repo_dir, "map-links-live")
    assert outcome.vacuous and not outcome.ok
    assert not check(repo_dir, only=["map-links-live"]).ok


def test_links_that_climb_out_of_a_subdirectory_resolve_relative_to_the_linking_file(repo_dir: Path) -> None:
    write(repo_dir, "docs/guides/README.md", "# Guides\n[the other one](../other.md)\n")
    write(repo_dir, "docs/other.md", "# Other\n")
    edit(
        repo_dir,
        "docs/00-READ-FIRST.md",
        "| must coordinate",
        "| follow a guide | [Guides](guides/README.md) |\n| must coordinate",
    )
    assert findings(repo_dir, "map-complete") == []
    assert findings(repo_dir, "map-links-live") == []


def test_a_link_that_escapes_the_repository_is_not_followed(repo_dir: Path) -> None:
    with (repo_dir / "docs" / "00-READ-FIRST.md").open("a", encoding="utf-8") as handle:
        handle.write("\n[outside](../../../etc/passwd)\n")
    assert findings(repo_dir, "map-links-live") == []
