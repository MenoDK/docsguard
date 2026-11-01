from __future__ import annotations

from pathlib import Path

from docsguard import scaffold
from docsguard.checks import RULES

from .conftest import check


def test_a_fresh_template_passes_every_guard(repo_dir: Path) -> None:
    report = check(repo_dir)
    assert report.ok, [f.render() for f in report.findings]
    assert {r.rule for r in report.results} == set(RULES)


def test_every_guard_examined_something_on_the_template(repo_dir: Path) -> None:
    # A guard that passes by looking at nothing proves nothing; the template must give each one real input.
    examined = {r.rule: r.examined for r in check(repo_dir).results}
    assert all(count > 0 for count in examined.values()), examined


def test_placeholders_are_filled_and_none_is_left_behind(repo_dir: Path) -> None:
    leftovers = [
        p.relative_to(repo_dir).as_posix()
        for p in repo_dir.rglob("*")
        if p.is_file() and ("{{" in p.read_text(encoding="utf-8") or "}}" in p.read_text(encoding="utf-8"))
    ]
    assert leftovers == []
    assert "demo" in (repo_dir / "CLAUDE.md").read_text(encoding="utf-8")


def test_hidden_directories_are_installed_under_their_real_names(repo_dir: Path) -> None:
    assert (repo_dir / ".claude" / "settings.json").is_file()
    assert not any(p.name.startswith("dot-") for p in repo_dir.rglob("*"))


def test_init_never_overwrites_existing_files_unless_forced(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("mine", encoding="utf-8")
    created, skipped = scaffold.init(tmp_path, "demo")
    assert "CLAUDE.md" in skipped
    assert "CLAUDE.md" not in created
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "mine"

    created, _ = scaffold.init(tmp_path, "demo", force=True)
    assert "CLAUDE.md" in created
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") != "mine"


def test_claude_md_stays_small_enough_to_be_followed(repo_dir: Path) -> None:
    assert len((repo_dir / "CLAUDE.md").read_text(encoding="utf-8").splitlines()) <= 60
