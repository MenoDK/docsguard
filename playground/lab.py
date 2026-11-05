"""The playground's model: a sample project, a catalogue of ways to break its documentation, and the real guards.

Nothing here imitates a guard. ``check`` calls ``docsguard.checks.run_checks``. The hooks are the same ``run``
functions the CLI hands to Claude Code, fed the same JSON, and what they print is returned unchanged.

The sample is rebuilt from the template every time something changes. The state is the *set* of active breaks (and the
authorization lines a visitor wrote), so putting a break back cannot leave residue, and two breaks that edit the same
file cannot undo each other. Everything lives in one temporary directory that the process owns and removes on exit.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, TextIO

from docsguard import budget_report, checks, scaffold
from docsguard.config import load
from docsguard.hooks import git_guard, scope_guard
from docsguard.repo import Repo

SAMPLE: Final = "sample-shop"
# What the rendered output says instead of the temporary directory, so a transcript does not depend on where it ran.
LABEL: Final = "/work/sample-shop"
HANDOFF: Final = "docs/HANDOFF.md"
MAP: Final = "docs/00-READ-FIRST.md"

EDIT_TOOLS: Final = ("Edit", "Write", "MultiEdit", "NotebookEdit")
MAX_COMMAND: Final = 2000
MAX_TARGET: Final = 300
MAX_AUTHORIZATIONS: Final = 12
_NEEDLE = re.compile(r"^[A-Za-z0-9_./*-]{1,60}$")
_REASON = re.compile(r"^[^\x00-\x1f\x7f]{0,120}$")  # one line: a newline would write a second authorization
_WIRE = re.compile(r"^\[docsguard:(?P<rule>[^\]]+)\] (?P<reason>.*)$", re.DOTALL)


class LabError(ValueError):
    """The request is not one the lab can act on. The message is safe to show."""


class BreakError(RuntimeError):
    """The sample no longer looks like the template, so a break cannot find the text it edits."""


def _edit(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise BreakError(f"{relative} no longer contains the text this break edits")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _append(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def _orphan(root: Path) -> None:
    (root / "docs/runbook.md").write_text(
        "# Runbook\n\nHow to restart the shop, written in a hurry and never added to the map.\n", encoding="utf-8"
    )


def _dead_link(root: Path) -> None:
    _edit(root, MAP, "(CHECKLIST.md)", "(PLAN.md)")


def _count(root: Path) -> None:
    _edit(root, MAP, "expect=1", "expect=4")


def _adr(root: Path) -> None:
    _edit(root, "docs/adr/0001-record-architecture-decisions.md", "## Rejected alternatives", "## Notes")


def _handoff(root: Path) -> None:
    marker = "## 8. Suite state"
    text = (root / HANDOFF).read_text(encoding="utf-8")
    if marker not in text:
        raise BreakError(f"{HANDOFF} no longer contains the text this break edits")
    (root / HANDOFF).write_text(
        text.split(marker)[0] + marker + "\n\nEverything passes, as expected.\n", encoding="utf-8"
    )


def _bloat(root: Path) -> None:
    rule = "remember to be careful, thorough and consistent about absolutely everything, every single time, always."
    _append(root, "CLAUDE.md", "\n".join(f"- Rule {n}: {rule}" for n in range(1, 261)) + "\n")


def _skill(root: Path) -> None:
    _edit(root, ".claude/skills/handoff/SKILL.md", "description: Use when ending", "description: Handles ending")


def _secret(root: Path) -> None:
    # Built here, in two pieces, so this file is not itself a thing a secret scanner has to explain.
    key = "AKIA" + "QZ7K3WP9XV2MD4HB"
    _append(root, HANDOFF, f"\nDeploy key: {key}\n")


def _entrypoint(root: Path) -> None:
    _edit(
        root,
        "CLAUDE.md",
        "- Map of every document: [docs/00-READ-FIRST.md](docs/00-READ-FIRST.md). "
        "Open a document only when the map says to.\n",
        "",
    )


def _exemption(root: Path) -> None:
    _append(
        root,
        "docsguard.toml",
        '\n[[exempt]]\nrule = "map-complete"\npath = "docs/generated/api.md"\nreason = "generated on every build"\n',
    )


@dataclass(frozen=True, slots=True)
class Break:
    id: str
    guard: str  # the guard that must notice it
    title: str
    summary: str
    apply: Callable[[Path], None]


# In the order of the guards, which is the order the lab shows them in.
BREAKS: Final[tuple[Break, ...]] = (
    Break(
        "entrypoint",
        "claude-entrypoint",
        "Forget to point CLAUDE.md at the map",
        "The file every session loads no longer says where the documents are.",
        _entrypoint,
    ),
    Break(
        "dead-link",
        "map-links-live",
        "Point the map at a file that is gone",
        "One row of the map links to PLAN.md, which was never there. What that row led to is now unreachable too.",
        _dead_link,
    ),
    Break(
        "orphan-doc",
        "map-complete",
        "Add a runbook and forget the map",
        "A new document under docs/ that nothing links to: a session that follows the map will never find it.",
        _orphan,
    ),
    Break(
        "count-drift",
        "map-counts",
        "Say there are four decisions when there is one",
        "The map declares how many records the folder holds. Now it declares a number the disk does not have.",
        _count,
    ),
    Break(
        "adr-no-rejected",
        "adr-shape",
        "Write a decision without the alternatives that lost",
        "The record keeps its title and its status, and loses the section that says what was not chosen and why.",
        _adr,
    ),
    Break(
        "handoff-no-number",
        "handoff-shape",
        "Report the suite state without a number",
        "“Everything passes, as expected.” Nothing was measured, so nothing can be wrong.",
        _handoff,
    ),
    Break(
        "bloat",
        "instruction-budget",
        "Grow CLAUDE.md to nearly three hundred lines",
        "Every rule is reasonable. Together they are loaded on every turn, and long instructions are followed less "
        "well.",
        _bloat,
    ),
    Break(
        "skill-no-trigger",
        "skill-shape",
        "Describe a skill without saying when it applies",
        "A skill is found by its description. “Handles ending…” never says when to reach for it.",
        _skill,
    ),
    Break(
        "secret",
        "no-secrets",
        "Paste a cloud access key into the handoff",
        "Documents are copied into prompts and exported. The key is made up here, but the guard does not know that.",
        _secret,
    ),
    Break(
        "stale-exemption",
        "exemptions",
        "Keep a dismissal for a file that no longer exists",
        "A written exception that matches nothing any more is reported, so exceptions cannot quietly rot.",
        _exemption,
    ),
)
_BY_ID: Final = {b.id: b for b in BREAKS}


def _run_hook(run: Callable[[TextIO, TextIO], int], payload: dict[str, Any]) -> dict[str, Any]:
    """Feed a hook the JSON Claude Code would send and report what it printed."""
    stdout = io.StringIO()
    run(io.StringIO(json.dumps(payload)), stdout)
    wire = stdout.getvalue().strip()
    if not wire:
        return {"allowed": True, "rule": None, "reason": None, "wire": ""}
    message = json.loads(wire)["hookSpecificOutput"]["permissionDecisionReason"]
    parsed = _WIRE.match(message)
    return {
        "allowed": False,
        "rule": parsed.group("rule") if parsed else None,
        "reason": parsed.group("reason") if parsed else message,
        "wire": wire,
    }


class Lab:
    """One sample project, owned by this object. Every public method takes the lock, so a request sees a whole state."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._base = Path(tempfile.mkdtemp(prefix="docsguard-playground-"))
        self.root = self._base / SAMPLE
        self._active: list[str] = []
        self._authorizations: list[str] = []
        self._rebuild()

    def close(self) -> None:
        shutil.rmtree(self._base, ignore_errors=True)

    def _rebuild(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)
        scaffold.init(self.root, SAMPLE)
        for brk in BREAKS:
            if brk.id in self._active:
                brk.apply(self.root)
        if self._authorizations:
            _append(self.root, ".claude/authorizations.txt", "\n".join(self._authorizations) + "\n")

    # ------------------------------------------------------------------ what can be changed

    def reset(self) -> None:
        with self._lock:
            self._active = []
            self._authorizations = []
            self._rebuild()

    def set_break(self, break_id: str, on: bool) -> None:
        if break_id not in _BY_ID:
            raise LabError(f"unknown break: {break_id!r}")
        with self._lock:
            wanted = {*self._active, break_id} if on else {*self._active} - {break_id}
            self._active = [b.id for b in BREAKS if b.id in wanted]
            self._rebuild()

    def authorize(self, needle: str, reason: str) -> str:
        """Write one authorization line, the way a human would. An empty reason writes the line the hook must ignore."""
        if not _NEEDLE.match(needle):
            raise LabError("the path must be 1 to 60 characters of letters, digits and . _ / * -")
        if not _REASON.match(reason):
            raise LabError("the reason must be one line of at most 120 characters")
        line = f"path:{needle} -- {reason}" if reason.strip() else f"path:{needle}"
        with self._lock:
            if len(self._authorizations) >= MAX_AUTHORIZATIONS:
                raise LabError("enough authorizations for a demonstration: start over to clear them")
            self._authorizations.append(line)
            self._rebuild()
        return line

    # ------------------------------------------------------------------ what can be asked

    def overview(self) -> dict[str, Any]:
        with self._lock:
            active = set(self._active)
            return {
                "sample": SAMPLE,
                "rules": [{"name": name, "meaning": meaning} for name, (_, meaning) in checks.RULES.items()],
                "breaks": [
                    {"id": b.id, "guard": b.guard, "title": b.title, "summary": b.summary, "active": b.id in active}
                    for b in BREAKS
                ],
                "authorizations": list(self._authorizations),
            }

    def check(self) -> dict[str, Any]:
        with self._lock:
            repo = Repo(self.root)
            report = checks.run_checks(repo, load(self.root))
            return {
                "ok": report.ok,
                "problems": len(report.findings) + sum(1 for r in report.results if r.vacuous),
                "rendered": checks.render(report, LABEL),
                "rules": [
                    {
                        "rule": r.rule,
                        "examined": r.examined,
                        "skipped": r.skipped,
                        "vacuous": r.vacuous,
                        "ok": r.ok,
                        "findings": [{"path": f.path, "line": f.line, "message": f.message} for f in r.findings],
                    }
                    for r in report.results
                ],
            }

    def files(self) -> list[dict[str, Any]]:
        with self._lock:
            found = sorted(p for p in self.root.rglob("*") if p.is_file())
            return [{"path": p.relative_to(self.root).as_posix(), "bytes": p.stat().st_size} for p in found]

    def budget(self) -> dict[str, Any]:
        with self._lock:
            data = budget_report.build(Repo(self.root), load(self.root))
            return {**data, "rendered": budget_report.render(data)}

    def hook_git(self, command: str) -> dict[str, Any]:
        if not command.strip():
            raise LabError("type a command")
        if len(command) > MAX_COMMAND:
            raise LabError(f"a command of at most {MAX_COMMAND} characters")
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        return {"hook": "git-guard", "request": json.dumps(payload), **_run_hook(git_guard.run, payload)}

    def hook_scope(self, tool: str, target: str) -> dict[str, Any]:
        if tool != "Bash" and tool not in EDIT_TOOLS:
            raise LabError(f"tool must be one of {', '.join((*EDIT_TOOLS, 'Bash'))}")
        if not target.strip():
            raise LabError("type a path (or a command, for Bash)")
        if len(target) > (MAX_COMMAND if tool == "Bash" else MAX_TARGET):
            raise LabError("that is longer than the lab accepts")
        key = "command" if tool == "Bash" else ("notebook_path" if tool == "NotebookEdit" else "file_path")
        with self._lock:
            payload = {"tool_name": tool, "tool_input": {key: target}, "cwd": str(self.root)}
            answer = _run_hook(scope_guard.run, payload)
        shown = {**payload, "cwd": LABEL}
        return {"hook": "scope-guard", "request": json.dumps(shown), **answer}
