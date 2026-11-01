from __future__ import annotations

from pathlib import Path

from docsguard.budget_report import build
from docsguard.config import load
from docsguard.repo import Repo
from docsguard.rules.budget import session_set

from .conftest import findings, result, write


def paths(root: Path) -> list[str]:
    return [f.path for f in session_set(Repo(root))]


def test_session_start_is_claude_md_its_imports_and_unscoped_rules(repo_dir: Path) -> None:
    assert paths(repo_dir) == ["CLAUDE.md", "AGENTS.md", ".claude/rules/precedence.md"]


def test_a_path_scoped_rule_is_loaded_on_demand_so_it_is_not_charged(repo_dir: Path) -> None:
    write(repo_dir, ".claude/rules/api.md", "---\npaths: src/api/**\n---\n\n" + "rule\n" * 500)
    assert ".claude/rules/api.md" not in paths(repo_dir)
    assert findings(repo_dir, "instruction-budget") == []


def test_an_unscoped_rule_is_charged(repo_dir: Path) -> None:
    write(repo_dir, ".claude/rules/everywhere.md", "rule\n" * 250)
    found = findings(repo_dir, "instruction-budget")
    assert [f.path for f in found] == [".claude/rules/everywhere.md"]
    assert "250 lines exceeds the per-file cap of 200" in found[0].message


def test_imports_are_followed_transitively_and_cycles_terminate(repo_dir: Path) -> None:
    write(repo_dir, "AGENTS.md", "see @extra.md\n")
    write(repo_dir, "extra.md", "back to @AGENTS.md and @CLAUDE.md\n")
    assert paths(repo_dir) == ["CLAUDE.md", "AGENTS.md", "extra.md", ".claude/rules/precedence.md"]


def test_an_import_in_a_code_fence_or_inline_code_is_an_example_not_an_import(repo_dir: Path) -> None:
    write(repo_dir, "extra.md", "payload\n")
    with (repo_dir / "CLAUDE.md").open("a", encoding="utf-8") as handle:
        handle.write(
            """
Write `@extra.md` to import.

```
@extra.md
```
"""
        )
    assert "extra.md" not in paths(repo_dir)


def test_an_import_that_does_not_exist_is_ignored(repo_dir: Path) -> None:
    with (repo_dir / "CLAUDE.md").open("a", encoding="utf-8") as handle:
        handle.write(
            """
@missing.md
"""
        )
    assert paths(repo_dir) == ["CLAUDE.md", "AGENTS.md", ".claude/rules/precedence.md"]


def test_the_total_budget_is_enforced_even_when_every_file_is_small(repo_dir: Path) -> None:
    (repo_dir / "docsguard.toml").write_text("[budget]\nmax_session_tokens = 500\n", encoding="utf-8")
    found = findings(repo_dir, "instruction-budget")
    assert len(found) == 1 and "over the budget of 500" in found[0].message


def test_nothing_loaded_at_session_start_is_an_explicit_skip(repo_dir: Path) -> None:
    import shutil

    (repo_dir / "CLAUDE.md").unlink()
    # An unscoped rule is still loaded without CLAUDE.md, so the budget still applies to it.
    assert result(repo_dir, "instruction-budget").examined == 1
    shutil.rmtree(repo_dir / ".claude" / "rules")
    outcome = result(repo_dir, "instruction-budget")
    assert outcome.skipped and outcome.ok


def test_the_report_measures_session_start_against_reading_everything(repo_dir: Path) -> None:
    data = build(Repo(repo_dir), load(repo_dir))
    assert data["session_tokens"] == sum(f["tokens"] for f in data["session_start"])
    assert data["everything_tokens"] == data["session_tokens"] + sum(i["tokens"] for i in data["on_demand"])
    assert 0 < data["saving_percent"] < 100
    by_path = {i["path"]: i["tokens"] for i in data["on_demand"]}
    assert data["typical_start_tokens"] == (
        data["session_tokens"] + by_path["docs/00-READ-FIRST.md"] + by_path["docs/HANDOFF.md"]
    )
    assert data["typical_start_tokens"] > data["session_tokens"]
    on_demand = {i["path"] for i in data["on_demand"]}
    assert "docs/HANDOFF.md" in on_demand and "CLAUDE.md" not in on_demand


def test_archived_documents_do_not_inflate_the_cost_of_reading_everything(repo_dir: Path) -> None:
    before = build(Repo(repo_dir), load(repo_dir))["everything_tokens"]
    write(repo_dir, "docs/archive/old.md", "x" * 40_000)
    assert build(Repo(repo_dir), load(repo_dir))["everything_tokens"] == before
