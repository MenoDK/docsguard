"""The instruction budget: what every session pays before the first question is asked.

A session starts by loading ``CLAUDE.md``, whatever it imports with ``@path``, and every rule under
``.claude/rules/`` that is not scoped to particular paths. All of it is paid on every turn of every
session, so it is budgeted: a size cap per file and a cap on the total. Everything else lives in docs
that are opened on demand, via the map.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import Config
from ..model import Finding, RuleResult
from ..repo import Repo, front_matter, iter_prose_lines
from ..tokens import estimate_tokens

MAX_IMPORT_DEPTH = 5
_IMPORT = re.compile(r"(?:^|\s)@([\w./-]+\.[\w]+)")


@dataclass(frozen=True, slots=True)
class LoadedFile:
    path: str
    via: str  # "root" | "import" | "rule"
    lines: int
    tokens: int


def session_set(repo: Repo) -> list[LoadedFile]:
    """The files a fresh session loads at startup, in load order, each exactly once."""
    loaded: dict[str, LoadedFile] = {}

    def add(path: str, via: str, depth: int) -> None:
        if path in loaded or not repo.exists(path):
            return
        text = repo.read(path)
        loaded[path] = LoadedFile(path, via, len(text.splitlines()), estimate_tokens(text))
        if depth >= MAX_IMPORT_DEPTH:
            return
        for _, line in iter_prose_lines(text):
            for match in _IMPORT.finditer(re.sub(r"`[^`]*`", "", line)):
                target = repo.resolve_link(path, match.group(1))
                if target and repo.path(target).is_file():
                    add(target, "import", depth + 1)

    add("CLAUDE.md", "root", 0)
    for rule_file in sorted(repo.markdown_under(".claude/rules")):
        meta, _ = front_matter(repo.read(rule_file))
        if "paths" not in meta:  # path-scoped rules are loaded on demand, not at startup
            add(rule_file, "rule", 0)
    return list(loaded.values())


def instruction_budget(repo: Repo, config: Config) -> RuleResult:
    rule = "instruction-budget"
    files = session_set(repo)
    if not files:
        return RuleResult(rule, 0, skipped="no CLAUDE.md: nothing is loaded at session start")
    findings = [
        Finding(
            rule,
            f.path,
            f"{f.lines} lines exceeds the per-file cap of {config.max_lines_per_file}: "
            "long instructions are followed less reliably, and cost tokens on every turn",
        )
        for f in files
        if f.lines > config.max_lines_per_file
    ]
    total = sum(f.tokens for f in files)
    if total > config.max_session_tokens:
        findings.append(
            Finding(
                rule,
                "CLAUDE.md",
                f"the session-start set is ~{total} tokens, over the budget of {config.max_session_tokens} "
                f"({len(files)} files); move detail into on-demand docs",
            )
        )
    return RuleResult(rule, len(files), tuple(findings))
