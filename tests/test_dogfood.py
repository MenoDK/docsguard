"""The repository holds itself to its own rules. If these fail, the project is teaching what it does not practise."""

from __future__ import annotations

from pathlib import Path

from docsguard.checks import RULES, run_checks
from docsguard.config import load
from docsguard.repo import Repo

ROOT = Path(__file__).resolve().parents[1]


def test_this_repository_passes_every_one_of_its_own_guards() -> None:
    repo = Repo(ROOT)
    report = run_checks(repo, load(repo.root))
    assert report.ok, [f.render() for f in report.findings] + [r.rule for r in report.results if r.vacuous]


def test_none_of_the_guards_passes_vacuously_here() -> None:
    repo = Repo(ROOT)
    skipped = {r.rule: r.skipped for r in run_checks(repo, load(repo.root)).results if r.skipped}
    assert skipped == {}, skipped
    assert {r.rule for r in run_checks(repo, load(repo.root)).results if r.examined} == set(RULES)
