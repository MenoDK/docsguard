from __future__ import annotations

from pathlib import Path

from .conftest import edit, findings, result, write

SKILL = ".claude/skills/handoff/SKILL.md"


def messages(root: Path) -> list[str]:
    return [f.message for f in findings(root, "skill-shape")]


def test_the_template_skills_are_well_formed(repo_dir: Path) -> None:
    assert result(repo_dir, "skill-shape").examined == 3 and messages(repo_dir) == []


def test_the_name_must_equal_the_directory(repo_dir: Path) -> None:
    edit(repo_dir, SKILL, "name: handoff", "name: handover")
    assert any("must equal the directory 'handoff'" in m for m in messages(repo_dir))


def test_the_description_must_say_when_to_use_it(repo_dir: Path) -> None:
    edit(repo_dir, SKILL, "description: Use when ending", "description: Ends")
    assert any("Use when" in m for m in messages(repo_dir))


def test_a_missing_description_is_reported(repo_dir: Path) -> None:
    write(repo_dir, SKILL, "---\nname: handoff\n---\n\nbody\n")
    assert any("has no description" in m for m in messages(repo_dir))


def test_a_description_with_an_unquoted_colon_is_invalid_yaml_and_reported(repo_dir: Path) -> None:
    edit(repo_dir, SKILL, "after a break. Rewrites", "after a break: rewrites")
    assert any("YAML will mis-read" in m for m in messages(repo_dir))


def test_a_quoted_description_may_contain_a_colon(repo_dir: Path) -> None:
    edit(repo_dir, SKILL, "after a break. Rewrites", "after a break: rewrites")
    text = (repo_dir / SKILL).read_text(encoding="utf-8")
    (repo_dir / SKILL).write_text(
        text.replace("description: Use when", 'description: "Use when', 1).replace(
            "from disk alone.\n---", 'from disk alone."\n---', 1
        ),
        encoding="utf-8",
    )
    assert messages(repo_dir) == []


def test_a_body_too_large_to_survive_compaction_is_reported(repo_dir: Path) -> None:
    (repo_dir / "docsguard.toml").write_text("[budget]\nmax_skill_tokens = 100\n", encoding="utf-8")
    assert any("truncated after compaction" in m for m in messages(repo_dir))


def test_a_skill_directory_without_skill_md_and_a_file_without_front_matter(repo_dir: Path) -> None:
    (repo_dir / ".claude/skills/empty").mkdir()
    write(repo_dir, ".claude/skills/bare/SKILL.md", "# no front matter\n")
    found = findings(repo_dir, "skill-shape")
    assert {f.path for f in found} == {".claude/skills/empty/", ".claude/skills/bare/SKILL.md"}


def test_no_skills_directory_is_an_explicit_skip(repo_dir: Path) -> None:
    import shutil

    shutil.rmtree(repo_dir / ".claude/skills")
    outcome = result(repo_dir, "skill-shape")
    assert outcome.skipped and outcome.ok


def test_a_folded_block_scalar_description_is_read_across_lines(repo_dir: Path) -> None:
    write(
        repo_dir,
        SKILL,
        "---\nname: handoff\ndescription: >\n  Rewrites the handoff.\n  Use when ending a session.\n---\n\nbody\n",
    )
    assert messages(repo_dir) == []
