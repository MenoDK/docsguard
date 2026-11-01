from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any

import pytest

from docsguard.config import load
from docsguard.hooks.scope_guard import evaluate, glob_to_regex, load_authorizations, run, written_paths

from .conftest import write


def payload(tool: str, root: Path, **tool_input: Any) -> dict[str, Any]:
    return {"tool_name": tool, "tool_input": tool_input, "cwd": str(root)}


def decide(root: Path, tool: str, **tool_input: Any) -> str | None:
    decision = evaluate(payload(tool, root, **tool_input), root.resolve(), load(root))
    return decision.reason if decision else None


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "config/.env",
        "certs/server.pem",
        "k/private.key",
        "deploy/id_rsa",
        ".ssh/config",
        ".git/config",
    ],
)
def test_writing_secret_bearing_paths_is_denied(repo_dir: Path, path: str) -> None:
    for tool in ("Edit", "Write", "MultiEdit"):
        reason = decide(repo_dir, tool, file_path=str(repo_dir / path))
        assert reason is not None and "is blocked by" in reason, (tool, path)


@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        ".env.sample",
        "src/app.py",
        "docs/notes.md",
        "environment.md",
        "keyboard.md",
        "src/key_handler.py",
    ],
)
def test_ordinary_paths_and_env_templates_are_allowed(repo_dir: Path, path: str) -> None:
    assert decide(repo_dir, "Write", file_path=str(repo_dir / path)) is None


def test_the_denial_gives_the_reason_the_path_is_protected_and_how_to_authorize(repo_dir: Path) -> None:
    reason = decide(repo_dir, "Edit", file_path=".env")
    assert reason is not None
    assert "real credentials" in reason
    assert "path:.env -- <why>" in reason and ".claude/authorizations.txt" in reason


def test_relative_paths_traversal_and_symlinks_cannot_dodge_the_rule(repo_dir: Path) -> None:
    assert decide(repo_dir, "Write", file_path="docs/../.env") is not None
    assert decide(repo_dir, "Write", file_path="./.env") is not None
    (repo_dir / "link.txt").symlink_to(repo_dir / ".env")
    assert decide(repo_dir, "Write", file_path=str(repo_dir / "link.txt")) is not None


def test_an_absolute_ssh_path_outside_the_repository_is_protected_too(repo_dir: Path) -> None:
    assert decide(repo_dir, "Write", file_path=str(Path.home() / ".ssh" / "authorized_keys")) is not None


def test_reads_are_never_blocked(repo_dir: Path) -> None:
    assert decide(repo_dir, "Read", file_path=".env") is None
    assert decide(repo_dir, "Grep", pattern="x", path=".env") is None
    assert decide(repo_dir, "Bash", command="cat .env") is None
    assert decide(repo_dir, "Bash", command="grep -r TOKEN .env certs/") is None
    assert decide(repo_dir, "Bash", command="cp .env /tmp/backup-of-env") is None  # copying FROM it only reads it


@pytest.mark.parametrize(
    "command",
    [
        "echo SECRET=1 > .env",
        "echo SECRET=1 >> .env",
        "echo SECRET=1 >.env",
        "cat x | tee .env",
        "tee -a .env < x",
        "rm .env",
        "rm -f certs/server.pem",
        "mv notes.txt .env",
        "cp notes.txt .env",
        "sed -i 's/a/b/' .env",
        "sed -i -e 's/a/b/' .env",
        "truncate -s 0 .env",
        "dd if=/dev/zero of=.env",
        "touch .env",
        "bash -c 'echo x > .env'",
        "echo $(echo x > .env)",
        "cd src && echo x > ../.env",
    ],
)
def test_shell_commands_that_write_a_protected_path_are_denied(repo_dir: Path, command: str) -> None:
    reason = decide(repo_dir, "Bash", command=command)
    assert reason is not None, command


@pytest.mark.parametrize(
    "command",
    [
        "echo hi > notes.txt",
        "echo hi > /dev/null",
        "ls > /dev/null 2>&1",
        "cat a b > c",
        "rm -rf build",
        "echo hi >> .env.example",
        "git add .env.example",
    ],
)
def test_harmless_shell_writes_are_allowed(repo_dir: Path, command: str) -> None:
    assert decide(repo_dir, "Bash", command=command) is None


def test_a_written_authorization_with_a_reason_permits_exactly_that_path(repo_dir: Path) -> None:
    write(
        repo_dir,
        ".claude/authorizations.txt",
        "# rotate staging creds\npath:config/.env.staging -- rotating after the incident, until 2026-12-01\n",
    )
    assert decide(repo_dir, "Write", file_path="config/.env.staging") is None
    assert decide(repo_dir, "Write", file_path="config/.env.production") is not None


def test_an_authorization_without_a_reason_is_ignored_and_the_denial_says_so(repo_dir: Path) -> None:
    write(repo_dir, ".claude/authorizations.txt", "path:.env\n")
    reason = decide(repo_dir, "Write", file_path=".env")
    assert reason is not None and "1 authorization line(s) were ignored because they give no reason" in reason
    auth = load_authorizations(repo_dir, load(repo_dir))
    assert auth.needles == () and auth.ignored == ("path:.env",)


def test_comments_and_blank_lines_in_the_authorizations_file_are_fine(repo_dir: Path) -> None:
    write(repo_dir, ".claude/authorizations.txt", "\n# comment\n\npath:x.pem -- vendored test fixture, public\n")
    assert load_authorizations(repo_dir, load(repo_dir)).needles == ("x.pem",)


def test_project_specific_protected_paths_come_from_the_config_and_carry_their_reason(repo_dir: Path) -> None:
    with (repo_dir / "docsguard.toml").open("a", encoding="utf-8") as handle:
        handle.write(
            '\n[[scope.protected]]\npattern = "infra/production/**"\nreason = "production changes go through review"\n'
        )
    reason = decide(repo_dir, "Edit", file_path="infra/production/main.tf")
    assert reason is not None and "production changes go through review" in reason
    assert decide(repo_dir, "Edit", file_path="infra/staging/main.tf") is None
    assert decide(repo_dir, "Edit", file_path=".env") is not None  # defaults still apply


def test_defaults_can_be_switched_off_explicitly(repo_dir: Path) -> None:
    (repo_dir / "docsguard.toml").write_text("[scope]\nextend_defaults = false\n", encoding="utf-8")
    assert decide(repo_dir, "Edit", file_path=".env") is None


def test_unknown_tools_are_ignored(repo_dir: Path) -> None:
    assert decide(repo_dir, "WebFetch", url="https://example.com") is None


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        (".env", ".env", True),
        (".env", "a/b/.env", True),
        (".env", "x.env", False),
        (".env.*", ".env.local", True),
        ("**/*.pem", "a/b/c.pem", True),
        ("**/*.pem", "c.pem", True),
        ("**/*.pem", "c.pem.txt", False),
        ("infra/**", "infra/a/b.tf", True),
        ("infra/**", "other/infra/a.tf", False),
        ("a/*/c", "a/b/c", True),
        ("a/*/c", "a/b/x/c", False),
        ("a?c", "abc", True),
        ("a?c", "a/c", False),
    ],
)
def test_glob_semantics(pattern: str, path: str, expected: bool) -> None:
    assert bool(glob_to_regex(pattern).match(path)) is expected


def test_written_paths_extracts_targets_not_sources() -> None:
    assert written_paths("cp a b") == ["b"]
    assert written_paths("mv a b") == ["a", "b"]
    assert written_paths("echo x > out.txt") == ["out.txt"]
    assert written_paths("cat a") == []


def hook(data: object, cwd: Path) -> tuple[int, str]:
    out = io.StringIO()
    previous = Path.cwd()
    os.chdir(cwd)
    try:
        code = run(io.StringIO(json.dumps(data)), out)
    finally:
        os.chdir(previous)
    return code, out.getvalue()


def test_the_hook_denies_with_the_pretooluse_wire_format(repo_dir: Path) -> None:
    code, out = hook(payload("Write", repo_dir, file_path=".env"), repo_dir)
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny" and decision["permissionDecisionReason"].startswith(
        "[docsguard:protected-path]"
    )


def test_the_hook_is_silent_for_allowed_writes_and_for_garbage_input(repo_dir: Path) -> None:
    assert hook(payload("Write", repo_dir, file_path="src/a.py"), repo_dir) == (0, "")
    out = io.StringIO()
    assert run(io.StringIO("}{"), out) == 0 and out.getvalue() == ""
