"""Same-commit discipline: a document is mapped in the commit that creates it.

The other guards check the tree. This one checks the *change*: with ``check --staged`` it fails when a
commit adds a document under ``docs/`` without touching the map (or, for an ADR, the ADR index). That is
the moment the index goes stale, and the cheapest moment to prevent it.
"""

from __future__ import annotations

import subprocess

from ..config import Config
from ..model import Finding, RuleResult
from ..repo import Repo


def staged_changes(repo: Repo) -> dict[str, str] | None:
    """``{path: status letter}`` of the index, or ``None`` when this is not a git work tree."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo.root), "diff", "--cached", "--name-status", "-z", "--no-renames"],
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    parts = [p for p in out.split("\0") if p]
    return {parts[i + 1]: parts[i] for i in range(0, len(parts) - 1, 2)}


def same_commit(repo: Repo, config: Config) -> RuleResult:
    rule = "same-commit"
    changes = staged_changes(repo)
    if changes is None:
        return RuleResult(rule, 0, skipped="not a git work tree (or git is not installed)")
    archived = tuple(d.rstrip("/") + "/" for d in config.archive_dirs)
    docs_prefix = config.docs_dir.rstrip("/") + "/"
    adr_prefix = config.adr_dir.rstrip("/") + "/"
    adr_index = adr_prefix + "README.md"
    added = [
        p
        for p, status in sorted(changes.items())
        if status == "A"
        and p.startswith(docs_prefix)
        and p.endswith(".md")
        and not p.startswith(archived)
        and p not in (config.map_file, adr_index)
    ]
    if not added:
        return RuleResult(rule, 0, skipped="no document was added in this commit")
    findings: list[Finding] = []
    for path in added:
        if path.startswith(adr_prefix):
            if adr_index not in changes:
                findings.append(Finding(rule, path, f"new ADR without {adr_index} in the same commit"))
        elif config.map_file not in changes:
            findings.append(Finding(rule, path, f"new document without {config.map_file} in the same commit"))
    return RuleResult(rule, len(added), tuple(findings))
