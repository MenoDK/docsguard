"""Fixtures. The "good repository" is the shipped template, initialised: if the template ever fails its own
guards, nearly every test here fails with it, which is exactly the property we want."""

from __future__ import annotations

from pathlib import Path

import pytest

from docsguard import scaffold
from docsguard.checks import Report, run_checks
from docsguard.config import load
from docsguard.model import Finding, RuleResult
from docsguard.repo import Repo


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    scaffold.init(root, "demo")
    return root


def check(root: Path, *, staged: bool = False, only: list[str] | None = None) -> Report:
    repo = Repo(root)
    return run_checks(repo, load(repo.root), staged=staged, only=only)


def result(root: Path, rule: str) -> RuleResult:
    return check(root, only=[rule]).results[0]


def findings(root: Path, rule: str) -> list[Finding]:
    return list(result(root, rule).findings)


def edit(root: Path, rel: str, old: str, new: str) -> None:
    """Replace ``old`` exactly once. Fails loudly when the template drifted, so a test never silently tests nothing."""
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{rel}: expected exactly one occurrence of {old!r}, found {text.count(old)}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
