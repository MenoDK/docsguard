from __future__ import annotations

import io
import json

import pytest

from docsguard.hooks.git_guard import evaluate, parse_args, run

# command -> the rule that must deny it
DENIED = [
    # force pushes, in every spelling
    ("git push --force", "force-push"),
    ("git push -f origin main", "force-push"),
    ("git push origin main -f", "force-push"),
    ("git push -fu origin main", "force-push"),
    ("git push --force-if-includes --force", "force-push"),
    ("git push origin +main", "force-push"),
    ("git push --mirror", "force-push"),
    # remote deletion
    ("git push origin --delete feature", "remote-delete"),
    ("git push origin :feature", "remote-delete"),
    ("git push -d origin feature", "remote-delete"),
    ("git push --prune origin", "remote-delete"),
    # discarding work
    ("git reset --hard", "reset-hard"),
    ("git reset --hard HEAD~3", "reset-hard"),
    ("git clean -fd", "clean"),
    ("git clean -f", "clean"),
    ("git clean --force -x", "clean"),
    ("git clean -fdx", "clean"),
    ("git checkout .", "discard-changes"),
    ("git checkout -- .", "discard-changes"),
    ("git checkout feature -- .", "discard-changes"),
    ("git checkout -f main", "discard-changes"),
    ("git restore .", "discard-changes"),
    ("git restore --worktree .", "discard-changes"),
    ("git restore --source=HEAD~2 :/", "discard-changes"),
    ("git restore --staged --worktree .", "discard-changes"),
    # branches, stashes, history
    ("git branch -D feature", "branch-delete"),
    ("git branch -d -f feature", "branch-delete"),
    ("git branch --delete --force feature", "branch-delete"),
    ("git branch -f main HEAD~5", "branch-reset"),
    ("git stash drop", "stash-drop"),
    ("git stash clear", "stash-drop"),
    ("git reflog expire --expire=now --all", "reflog"),
    ("git reflog delete HEAD@{1}", "reflog"),
    ("git gc --prune=now", "gc-prune"),
    ("git update-ref -d refs/heads/main", "ref-delete"),
    ("git filter-branch --tree-filter x", "history-rewrite"),
    ("git filter-repo --path src", "history-rewrite"),
    ("git worktree remove --force ../wt", "worktree-remove"),
    # bypassing the checks that exist to stop a bad commit
    ("git commit --no-verify -m x", "hooks-bypass"),
    ("git commit -n -m x", "hooks-bypass"),
    ("git commit -nm x", "hooks-bypass"),
    ("git push --no-verify", "hooks-bypass"),
    ("git merge --no-verify topic", "hooks-bypass"),
    ("git -c core.hooksPath=/dev/null commit -m x", "hooks-bypass"),
    ("git -c core.hookspath=/tmp/h commit -m x", "hooks-bypass"),
    # disguised: wrappers, chains, substitutions, nested shells, global options
    ("sudo git reset --hard", "reset-hard"),
    ("sudo -u deploy git push -f", "force-push"),
    ("env GIT_TRACE=1 git reset --hard", "reset-hard"),
    ("GIT_TRACE=1 git reset --hard", "reset-hard"),
    ("timeout 30 git clean -fd", "clean"),
    ("/usr/bin/git reset --hard", "reset-hard"),
    ("git -C ../other reset --hard", "reset-hard"),
    ("git --no-pager -C /repo push --force", "force-push"),
    ("git --git-dir=/x/.git reset --hard", "reset-hard"),
    ("npm test && git reset --hard", "reset-hard"),
    ("git status; git push -f", "force-push"),
    ("false || git clean -fd", "clean"),
    ("git log | head; git reset --hard", "reset-hard"),
    ("echo ok\ngit reset --hard", "reset-hard"),
    ("if true; then git reset --hard; fi", "reset-hard"),
    ("echo $(git reset --hard)", "reset-hard"),
    ("echo `git clean -fd`", "clean"),
    ('bash -c "git reset --hard"', "reset-hard"),
    ("sh -c 'cd x && git push --force'", "force-push"),
    ("eval 'git reset --hard'", "reset-hard"),
    ("find . -name x | xargs git rm -rf && git reset --hard", "reset-hard"),
    ("git reset --hard 2>&1 | tee out.log", "reset-hard"),
    ("git push --force 2>&1", "force-push"),
]

# Commands that look dangerous to a naive grep but are not, plus the ordinary day-to-day set.
ALLOWED = [
    "git status",
    "git diff --stat",
    "git log --oneline -20",
    "git add -A",
    "git commit -m 'fix: reset --hard is documented in the README'",
    "git commit -m \"$(cat <<'EOF'\nnotes about git push --force and git reset --hard\nEOF\n)\"",
    "git commit --amend --no-edit",
    "git push",
    "git push -u origin main",
    "git push --force-with-lease",
    "git push --force-with-lease origin feature",
    "git push --dry-run origin main",
    "git push -n origin main",
    "git pull --rebase",
    "git fetch --prune",
    "git checkout main",
    "git checkout -b feature",
    "git checkout -- src/app.py",
    "git switch main",
    "git restore --staged .",
    "git restore --staged -- .",
    "git restore src/app.py",
    "git reset",
    "git reset --soft HEAD~1",
    "git reset --mixed HEAD~1",
    "git clean -n",
    "git clean -nfd",
    "git clean --dry-run -fd",
    "git branch",
    "git branch -d merged-feature",
    "git branch -m old new",
    "git stash",
    "git stash push -m wip",
    "git stash pop",
    "git stash list",
    "git rebase main",
    "git merge topic",
    "git tag v1.0",
    "git reflog",
    "git gc",
    "git worktree add ../wt",
    "git worktree remove ../wt",
    "git -C ../other status",
    "echo 'git reset --hard' > notes.txt",
    "grep -r 'git push --force' docs/",
    "cat README.md",
    "ls -la",
    "rm -rf build/",
    "npm run build && npm test",
    "gh pr create --title 'x'",
    "pip install gitpython",
    "digit --force",
    "",
    "   ",
]


@pytest.mark.parametrize(("command", "rule"), DENIED)
def test_destructive_commands_are_denied_with_the_right_reason(command: str, rule: str) -> None:
    decision = evaluate(command)
    assert decision is not None, f"was allowed: {command!r}"
    assert decision.rule == rule, f"{command!r}: expected {rule}, got {decision.rule}"
    assert decision.reason


@pytest.mark.parametrize("command", ALLOWED)
def test_ordinary_commands_are_allowed(command: str) -> None:
    assert evaluate(command) is None, f"was denied: {command!r}"


def test_every_denial_names_a_safer_alternative_or_the_next_step() -> None:
    """The refusal is also the instruction: a bare "no" just sends people looking for a way round."""
    hints = (
        "use ",
        "run ",
        "instead",
        "name the file",
        "stash",
        "ask ",
        "fix ",
        "create ",
        "apply ",
        "preview",
        "commit ",
    )
    bare = {
        command: decision.reason
        for command, _ in DENIED
        if (decision := evaluate(command)) is not None and not any(h in decision.reason.lower() for h in hints)
    }
    assert bare == {}


def test_short_option_clusters_stop_where_a_value_begins() -> None:
    # `-mfixing` is a message, not the flags m, f, i, x ...
    assert parse_args(["-mfixing-n-things"]).short == {"m"}
    assert evaluate("git commit -mfixing-n-things") is None
    assert parse_args(["-fdx"]).short == {"f", "d", "x"}


def hook(payload: object) -> tuple[int, str]:
    out = io.StringIO()
    code = run(io.StringIO(payload if isinstance(payload, str) else json.dumps(payload)), out)
    return code, out.getvalue()


def test_the_hook_answers_with_a_pretooluse_deny_decision() -> None:
    code, out = hook({"tool_name": "Bash", "tool_input": {"command": "git reset --hard"}})
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"].startswith("[docsguard:reset-hard]")


def test_the_hook_is_silent_when_allowing() -> None:
    assert hook({"tool_name": "Bash", "tool_input": {"command": "git status"}}) == (0, "")


@pytest.mark.parametrize(
    "payload",
    [
        "not json at all",
        "[]",
        "null",
        {},
        {"tool_name": "Read", "tool_input": {"file_path": "x"}},
        {"tool_name": "Bash"},
        {"tool_name": "Bash", "tool_input": {"command": 42}},
        {"tool_name": "Bash", "tool_input": "git reset --hard"},
    ],
)
def test_anything_the_hook_cannot_understand_is_allowed_never_blocked(payload: object) -> None:
    assert hook(payload) == (0, "")
