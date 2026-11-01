from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from .conftest import check, edit, result, write


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def git_repo(repo_dir: Path) -> Path:
    git(repo_dir, "init", "-q", "-b", "main")
    git(repo_dir, "config", "user.email", "t@example.test")
    git(repo_dir, "config", "user.name", "Test")
    git(repo_dir, "config", "commit.gpgsign", "false")
    git(repo_dir, "add", "-A")
    git(repo_dir, "commit", "-q", "-m", "init")
    return repo_dir


def staged(root: Path) -> list[str]:
    return [f.message for f in check(root, staged=True).findings if f.rule == "same-commit"]


def test_a_new_document_without_the_map_in_the_same_commit_fails(git_repo: Path) -> None:
    write(git_repo, "docs/runbook.md", "# Runbook\n")
    git(git_repo, "add", "docs/runbook.md")
    assert staged(git_repo) == ["new document without docs/00-READ-FIRST.md in the same commit"]


def test_staging_the_map_with_it_passes(git_repo: Path) -> None:
    write(git_repo, "docs/runbook.md", "# Runbook\n")
    edit(
        git_repo,
        "docs/00-READ-FIRST.md",
        "| must coordinate",
        "| operate it | [Runbook](runbook.md) |\n| must coordinate",
    )
    git(git_repo, "add", "-A")
    assert staged(git_repo) == []


def test_a_new_adr_needs_the_adr_index_in_the_same_commit(git_repo: Path) -> None:
    write(git_repo, "docs/adr/0002-x.md", "# 0002\n")
    git(git_repo, "add", "docs/adr/0002-x.md")
    assert staged(git_repo) == ["new ADR without docs/adr/README.md in the same commit"]


def test_modifying_an_existing_document_does_not_require_the_map(git_repo: Path) -> None:
    edit(git_repo, "docs/CHECKLIST.md", "todo | n/a |\n| 3", "doing | n/a |\n| 3")
    git(git_repo, "add", "-A")
    outcome = result(git_repo, "map-complete")
    assert outcome.ok
    assert next(r for r in check(git_repo, staged=True).results if r.rule == "same-commit").skipped


def test_without_git_the_rule_is_an_explicit_skip(repo_dir: Path) -> None:
    same = next(r for r in check(repo_dir, staged=True).results if r.rule == "same-commit")
    assert same.skipped == "not a git work tree (or git is not installed)"


def test_the_rule_only_runs_when_asked(git_repo: Path) -> None:
    assert "same-commit" not in {r.rule for r in check(git_repo).results}
