"""Deny the git commands that destroy work that cannot be recovered from the repository itself.

The list is organised by *class of damage*, not by command, and every denial names the safer
alternative, so the refusal is also the instruction. It is a denylist on purpose: an allowlist of git
commands blocks the new, harmless command nobody listed yet, and that is the false positive that gets a
hook removed.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from typing import Any, TextIO

from .protocol import Decision, emit_deny, read_payload, tool_input
from .shell import simple_commands

BROAD_PATHSPECS = frozenset({".", "./", ":/", ":/*", "*", ":(top)"})
_VALUE_LETTERS = frozenset("mFCcSo")  # short options whose value may be glued on: stop reading the cluster there
_GLOBAL_WITH_VALUE = frozenset({"-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"})
_HOOKED = frozenset({"commit", "push", "merge", "rebase", "am", "cherry-pick", "revert", "pull"})


@dataclass(slots=True)
class Args:
    long: set[str]
    short: set[str]
    positional: list[str]
    after_dd: list[str]

    @property
    def paths(self) -> list[str]:
        return [*self.positional, *self.after_dd]


def parse_args(tokens: list[str]) -> Args:
    parsed = Args(set(), set(), [], [])
    after_dd = False
    for word in tokens:
        if after_dd:
            parsed.after_dd.append(word)
        elif word == "--":
            after_dd = True
        elif word.startswith("--"):
            parsed.long.add(word.split("=", 1)[0])
            if "=" in word:
                parsed.long.add(word)
        elif word.startswith("-") and len(word) > 1:
            for letter in word[1:]:
                parsed.short.add(letter)
                if letter in _VALUE_LETTERS:
                    break
        else:
            parsed.positional.append(word)
    return parsed


def evaluate_git(args: list[str]) -> Decision | None:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "-c":
            setting = args[index + 1] if index + 1 < len(args) else ""
            if setting.lower().startswith("core.hookspath"):
                return Decision(
                    "hooks-bypass",
                    "overriding core.hooksPath skips the repository's hooks. "
                    "Fix the hook, or run it deliberately yourself.",
                )
            index += 2
        elif arg in _GLOBAL_WITH_VALUE:
            index += 2
        elif arg.startswith("-"):
            index += 1
        else:
            break
    if index >= len(args):
        return None
    sub, rest = args[index], parse_args(args[index + 1 :])

    if sub in _HOOKED and ("--no-verify" in rest.long or (sub == "commit" and "n" in rest.short)):
        return Decision(
            "hooks-bypass",
            f"`git {sub} --no-verify` skips the checks that exist to stop a bad commit. Fix what the hook reports.",
        )

    if sub == "push":
        forced = (
            "--force" in rest.long
            or "--mirror" in rest.long
            or "f" in rest.short
            or any(p.startswith("+") for p in rest.positional)
        )
        deleting = (
            "--delete" in rest.long
            or "--prune" in rest.long
            or "d" in rest.short
            or any(p.startswith(":") and len(p) > 1 for p in rest.positional)
        )
        if forced:
            return Decision(
                "force-push",
                "a forced push overwrites remote history. "
                "Use `--force-with-lease`, which refuses when someone else pushed.",
            )
        if deleting:
            return Decision(
                "remote-delete",
                "deleting a remote ref cannot be undone from here. Ask the owner to do it deliberately.",
            )
    elif sub == "reset" and "--hard" in rest.long:
        return Decision(
            "reset-hard",
            "`reset --hard` discards uncommitted work for good. Use `git stash` first, or `git reset --mixed`.",
        )
    elif (
        sub == "clean"
        and ("f" in rest.short or "--force" in rest.long)
        and not ("n" in rest.short or "--dry-run" in rest.long)
    ):
        return Decision(
            "clean",
            "`git clean -f` deletes untracked files permanently. Run `git clean -n` to preview, and delete by name.",
        )
    elif sub == "checkout":
        if "f" in rest.short or "--force" in rest.long:
            return Decision(
                "discard-changes", "`checkout --force` overwrites local changes. Stash or commit them first."
            )
        if any(p in BROAD_PATHSPECS for p in rest.paths):
            return Decision(
                "discard-changes",
                "`git checkout .` throws away every local change. Name the file, or `git stash` first.",
            )
    elif sub == "restore":
        staged_only = ("--staged" in rest.long or "S" in rest.short) and not (
            "--worktree" in rest.long or "W" in rest.short
        )
        if any(p in BROAD_PATHSPECS for p in rest.paths) and not staged_only:
            return Decision(
                "discard-changes",
                "`git restore .` throws away every local change. Name the file, or `git stash` first.",
            )
    elif sub == "branch":
        deleting = "D" in rest.short or "d" in rest.short or "--delete" in rest.long
        forced = "D" in rest.short or "f" in rest.short or "--force" in rest.long
        if deleting and forced:
            return Decision(
                "branch-delete",
                "`branch -D` drops commits that no other branch reaches. Use `-d`, which refuses unmerged work.",
            )
        if forced and not deleting:
            return Decision(
                "branch-reset",
                "`branch -f` moves a branch and can orphan commits. Create a new branch instead.",
            )
    elif sub == "stash" and rest.positional[:1] in (["drop"], ["clear"]):
        return Decision(
            "stash-drop",
            "dropping a stash deletes the only copy of that work. Apply it first, or ask the owner.",
        )
    elif sub == "reflog" and rest.positional[:1] in (["expire"], ["delete"]):
        return Decision(
            "reflog",
            "expiring the reflog removes the last way back from a mistake. "
            "Leave it to expire on its own, or ask the owner.",
        )
    elif sub == "gc" and any(opt in ("--prune=now", "--prune=all") for opt in rest.long):
        return Decision(
            "gc-prune",
            "`gc --prune=now` makes unreachable commits unrecoverable. Run a plain `git gc`, which keeps recent ones.",
        )
    elif sub == "update-ref" and ("d" in rest.short or "--delete" in rest.long):
        return Decision(
            "ref-delete",
            "deleting a ref by hand bypasses every safety check. Use `git branch -d` or `git tag -d` instead.",
        )
    elif sub in ("filter-branch", "filter-repo"):
        return Decision(
            "history-rewrite",
            "rewriting the whole history is a project decision, not a side effect. Ask the owner, and work on a copy.",
        )
    elif sub == "worktree" and rest.positional[:1] == ["remove"] and ("f" in rest.short or "--force" in rest.long):
        return Decision(
            "worktree-remove",
            "`worktree remove --force` deletes a work tree with uncommitted changes. "
            "Commit or stash there first, then remove it without --force.",
        )
    return None


def evaluate(command: str) -> Decision | None:
    """The first denial among every simple command in ``command``, or ``None`` to allow."""
    for tokens in simple_commands(command):
        if posixpath.basename(tokens[0]) == "git":
            decision = evaluate_git(tokens[1:])
            if decision:
                return decision
    return None


def run(stdin: TextIO, stdout: TextIO) -> int:
    payload: dict[str, Any] | None = read_payload(stdin)
    if not payload or payload.get("tool_name") != "Bash":
        return 0
    command = tool_input(payload).get("command")
    if not isinstance(command, str):
        return 0
    decision = evaluate(command)
    if decision:
        emit_deny(stdout, decision)
    return 0
