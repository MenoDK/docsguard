from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from docsguard.cli import main

from .conftest import edit, write

SRC = str(Path(__file__).resolve().parents[1] / "src")


def run_module(*args: str, stdin: str = "", cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """A real child process: this is how Claude Code invokes a hook."""
    env = {**os.environ, "PYTHONPATH": SRC}
    return subprocess.run(
        [sys.executable, "-m", "docsguard", *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_check_passes_on_a_good_repository_and_says_what_it_examined(
    repo_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check", "--root", str(repo_dir)]) == 0
    out = capsys.readouterr().out
    assert "OK" in out and "map-complete" in out and "examined" in out


def test_check_exits_1_and_names_the_culprit_when_a_guard_fails(
    repo_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo_dir, "docs/orphan.md", "# Orphan\n")
    assert main(["check", "--root", str(repo_dir)]) == 1
    out = capsys.readouterr().out
    assert "[map-complete] docs/orphan.md" in out and "FAILED: 1 problem(s)" in out


def test_a_guard_that_examined_nothing_fails_the_run(repo_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo_dir, "docs/00-READ-FIRST.md", "# Map\n[x](https://example.com)\n")
    assert main(["check", "--root", str(repo_dir), "--rule", "map-links-live"]) == 1
    assert "examined nothing" in capsys.readouterr().out


def test_json_output_is_machine_readable(repo_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo_dir, "docs/orphan.md", "# Orphan\n")
    assert main(["check", "--root", str(repo_dir), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False
    failing = [r for r in data["results"] if r["findings"]]
    assert [r["rule"] for r in failing] == ["map-complete"]
    assert failing[0]["findings"][0]["path"] == "docs/orphan.md"


def test_an_unknown_rule_name_is_a_usage_error_not_a_silent_pass(
    repo_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check", "--root", str(repo_dir), "--rule", "no-such-rule"]) == 2
    assert "unknown rule" in capsys.readouterr().err


def test_a_broken_config_is_exit_2_with_a_message(repo_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo_dir, "docsguard.toml", "bogus = 1\n")
    assert main(["check", "--root", str(repo_dir)]) == 2
    assert "unknown key" in capsys.readouterr().err


def test_budget_prints_a_table_and_json(repo_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["budget", "--root", str(repo_dir)]) == 0
    assert "Session start" in capsys.readouterr().out
    assert main(["budget", "--root", str(repo_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["session_tokens"] > 0


def test_rules_lists_every_guard(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rules"]) == 0
    out = capsys.readouterr().out
    for name in ("map-complete", "adr-shape", "handoff-shape", "instruction-budget", "same-commit"):
        assert name in out


def test_init_then_check_is_green_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init", str(tmp_path / "new"), "--name", "shop"]) == 0
    assert main(["check", "--root", str(tmp_path / "new")]) == 0
    assert "shop" in (tmp_path / "new" / "CLAUDE.md").read_text(encoding="utf-8")
    capsys.readouterr()


def test_a_real_process_denies_through_the_hook_entry_point() -> None:
    done = run_module(
        "hook", "git-guard", stdin=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push -f"}})
    )
    assert done.returncode == 0
    assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_real_process_stays_silent_when_it_allows() -> None:
    done = run_module(
        "hook", "git-guard", stdin=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    )
    assert (done.returncode, done.stdout) == (0, "")


def test_the_scope_hook_runs_as_a_real_process(repo_dir: Path) -> None:
    data = {"tool_name": "Write", "tool_input": {"file_path": ".env"}, "cwd": str(repo_dir)}
    done = run_module("hook", "scope-guard", stdin=json.dumps(data), cwd=repo_dir)
    assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_broken_config_never_blocks_the_session_through_a_hook(repo_dir: Path) -> None:
    edit(repo_dir, "docsguard.toml", "docs_dir", "docs_directory")
    data = {"tool_name": "Write", "tool_input": {"file_path": ".env"}, "cwd": str(repo_dir)}
    done = run_module("hook", "scope-guard", stdin=json.dumps(data), cwd=repo_dir)
    # exit 1 is a visible, non-blocking error in Claude Code; exit 2 would block the tool call.
    assert done.returncode == 1 and "unknown key" in done.stderr and done.stdout == ""


def test_version_flag() -> None:
    assert run_module("--version").stdout.startswith("docsguard ")
