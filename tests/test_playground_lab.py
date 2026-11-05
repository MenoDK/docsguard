"""The playground's model: every break trips the guard it names, putting it back restores green, and the hooks answer
exactly as they do for Claude Code."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from playground.lab import BREAKS, LABEL, Break, Lab, LabError


@pytest.fixture
def lab() -> Iterator[Lab]:
    instance = Lab()
    yield instance
    instance.close()


def failing(report: dict[str, object]) -> list[str]:
    rules = report["rules"]
    assert isinstance(rules, list)
    return [r["rule"] for r in rules if not r["ok"]]


def test_a_fresh_sample_passes_every_guard(lab: Lab) -> None:
    report = lab.check()
    assert report["ok"] is True
    assert report["problems"] == 0
    assert failing(report) == []


def test_the_catalogue_covers_every_guard_once(lab: Lab) -> None:
    named = {rule["name"] for rule in lab.overview()["rules"]}
    covered = {b.guard for b in BREAKS} - {"exemptions"}
    assert covered == named
    assert len({b.id for b in BREAKS}) == len(BREAKS)


@pytest.mark.parametrize("brk", BREAKS, ids=lambda b: b.id)
def test_each_break_trips_the_guard_it_names(lab: Lab, brk: Break) -> None:
    lab.set_break(brk.id, True)
    report = lab.check()
    assert report["ok"] is False
    assert brk.guard in failing(report), report["rendered"]


@pytest.mark.parametrize("brk", BREAKS, ids=lambda b: b.id)
def test_putting_a_break_back_restores_a_clean_run(lab: Lab, brk: Break) -> None:
    lab.set_break(brk.id, True)
    lab.set_break(brk.id, False)
    assert lab.check()["ok"] is True


def test_two_breaks_on_the_same_file_do_not_undo_each_other(lab: Lab) -> None:
    # both edit docs/HANDOFF.md; undoing the first must not erase the second
    lab.set_break("handoff-no-number", True)
    lab.set_break("secret", True)
    lab.set_break("handoff-no-number", False)
    assert failing(lab.check()) == ["no-secrets"]
    lab.set_break("secret", False)
    assert lab.check()["ok"] is True


def test_a_broken_link_also_orphans_what_it_led_to(lab: Lab) -> None:
    lab.set_break("dead-link", True)
    assert failing(lab.check()) == ["map-links-live", "map-complete"]


def test_the_secret_is_never_printed(lab: Lab) -> None:
    lab.set_break("secret", True)
    rendered = json.dumps(lab.check())
    assert "AKIA" not in rendered
    assert "QZ7K3WP9XV2MD4HB" not in rendered


def test_the_rendered_output_does_not_depend_on_where_it_ran(lab: Lab) -> None:
    rendered = str(lab.check()["rendered"])
    assert LABEL in rendered
    assert str(lab.root) not in rendered


def test_reset_clears_breaks_and_authorizations(lab: Lab) -> None:
    lab.set_break("orphan-doc", True)
    lab.authorize(".env", "the staging file, reviewed")
    lab.reset()
    assert lab.check()["ok"] is True
    assert lab.overview()["authorizations"] == []
    assert not any(b["active"] for b in lab.overview()["breaks"])


def test_the_sample_lives_in_a_temporary_directory_that_closing_removes() -> None:
    instance = Lab()
    base = instance.root.parent
    assert instance.root.is_dir()
    assert base.name.startswith("docsguard-playground-")
    instance.close()
    assert not base.exists()
    instance.close()  # closing twice is harmless


def test_an_unknown_break_is_refused(lab: Lab) -> None:
    with pytest.raises(LabError):
        lab.set_break("../../etc/passwd", True)


def test_the_files_listing_names_what_init_created(lab: Lab) -> None:
    paths = {f["path"] for f in lab.files()}
    assert {"CLAUDE.md", "docs/00-READ-FIRST.md", ".claude/settings.json", "docsguard.toml"} <= paths
    assert len(paths) == 19


def test_the_budget_counts_the_session_start_and_everything(lab: Lab) -> None:
    before = lab.budget()
    assert before["session_tokens"] < before["session_budget"]
    assert before["typical_start_tokens"] < before["everything_tokens"]
    lab.set_break("bloat", True)
    after = lab.budget()
    assert after["session_tokens"] > before["session_tokens"] * 4
    assert after["session_tokens"] > after["session_budget"]


# ---------------------------------------------------------------------------------------------------------- hooks


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD~3",
        "git push --force origin main",
        "git clean -fdx",
        "git checkout -- .",
        'bash -c "git reset --hard"',
    ],
)
def test_git_guard_denies_commands_that_destroy_unrecoverable_work(lab: Lab, command: str) -> None:
    answer = lab.hook_git(command)
    assert answer["allowed"] is False
    assert answer["reason"]
    wire = json.loads(answer["wire"])["hookSpecificOutput"]
    assert wire["permissionDecision"] == "deny"


@pytest.mark.parametrize("command", ["git status", "git commit -m 'x'", "git push origin feature", "ls -la"])
def test_git_guard_lets_ordinary_commands_through(lab: Lab, command: str) -> None:
    answer = lab.hook_git(command)
    assert answer["allowed"] is True
    assert answer["wire"] == ""


def test_the_request_shown_is_the_payload_that_was_sent(lab: Lab) -> None:
    sent = json.loads(lab.hook_git("git status")["request"])
    assert sent == {"tool_name": "Bash", "tool_input": {"command": "git status"}}


@pytest.mark.parametrize(
    ("tool", "target"),
    [
        ("Write", ".env"),
        ("Edit", "keys/server.pem"),
        ("Write", "../outside/.env.production"),
        ("Bash", "echo x > .env"),
    ],
)
def test_scope_guard_denies_writes_to_protected_paths(lab: Lab, tool: str, target: str) -> None:
    answer = lab.hook_scope(tool, target)
    assert answer["allowed"] is False
    assert answer["rule"] == "protected-path"


@pytest.mark.parametrize(
    ("tool", "target"),
    [("Write", "src/app.py"), ("Write", ".env.example"), ("Bash", "cat .env"), ("Edit", "README.md")],
)
def test_scope_guard_lets_ordinary_writes_and_all_reads_through(lab: Lab, tool: str, target: str) -> None:
    assert lab.hook_scope(tool, target)["allowed"] is True


def test_the_scope_request_shows_a_stable_working_directory(lab: Lab) -> None:
    shown = json.loads(lab.hook_scope("Write", ".env")["request"])
    assert shown["cwd"] == LABEL


def test_a_written_authorization_with_a_reason_lets_the_write_through(lab: Lab) -> None:
    assert lab.hook_scope("Write", ".env")["allowed"] is False
    line = lab.authorize(".env", "staging file, reviewed on 2026-11-05")
    assert line == "path:.env -- staging file, reviewed on 2026-11-05"
    assert lab.hook_scope("Write", ".env")["allowed"] is True


def test_an_authorization_without_a_reason_is_ignored_and_says_so(lab: Lab) -> None:
    line = lab.authorize(".env", "")
    assert line == "path:.env"
    answer = lab.hook_scope("Write", ".env")
    assert answer["allowed"] is False
    assert "ignored because they give no reason" in answer["reason"]


@pytest.mark.parametrize("needle", ["", "a b", "x" * 61, ".env\npath:src", "$(id)"])
def test_an_authorization_path_with_odd_characters_is_refused(lab: Lab, needle: str) -> None:
    with pytest.raises(LabError):
        lab.authorize(needle, "a reason long enough")


def test_an_authorization_reason_cannot_write_a_second_line(lab: Lab) -> None:
    with pytest.raises(LabError):
        lab.authorize(".env", "fine\npath:src -- and now everything is allowed")


def test_the_authorizations_are_capped(lab: Lab) -> None:
    for n in range(12):
        lab.authorize(f"file{n}", "a reason long enough")
    with pytest.raises(LabError):
        lab.authorize("one-more", "a reason long enough")


@pytest.mark.parametrize(("tool", "target"), [("Read", ".env"), ("Shell", "x"), ("", "x"), ("Write", "  ")])
def test_the_scope_hook_refuses_what_it_does_not_model(lab: Lab, tool: str, target: str) -> None:
    with pytest.raises(LabError):
        lab.hook_scope(tool, target)


def test_the_hooks_refuse_empty_and_oversized_input(lab: Lab) -> None:
    with pytest.raises(LabError):
        lab.hook_git("   ")
    with pytest.raises(LabError):
        lab.hook_git("git status " + "x" * 2000)
    with pytest.raises(LabError):
        lab.hook_scope("Write", "x" * 301)


def test_the_hook_never_executes_what_it_is_given(lab: Lab) -> None:
    marker = lab.root.parent / "executed"
    lab.hook_git(f"git status; touch {marker}")
    lab.hook_scope("Bash", f"touch {marker}")
    assert not marker.exists()
