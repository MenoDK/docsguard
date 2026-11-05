"""No secrets, and no infrastructure identifiers, in the documents an AI session reads.

Documentation is copied into prompts, exported, and committed. A credential pasted "just for the
example" or a production host name left in a runbook travels with it. The rule scans the text that
configures or documents a session and reports *which pattern* matched and *where*: never the match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import Config
from ..model import Finding, RuleResult
from ..repo import Repo

SCANNED_SUFFIXES = (".md", ".txt", ".json", ".toml", ".yml", ".yaml")
MAX_BYTES = 1_000_000
_PLACEHOLDER = re.compile(
    r"example|placeholder|changeme|change-me|your[-_ ]|xxx|\*{3,}|<[^>]+>|\$\{|\$\(|fake|dummy|redacted|sample|todo",
    re.IGNORECASE,
)
# Well-known development defaults that appear in every README (`user:password@localhost`). An exact match only:
# a substring test would let "password-9f3k2..." through.
_DEV_DEFAULTS = frozenset(
    {"password", "pass", "passwd", "secret", "postgres", "root", "admin", "user", "test", "changeme"}
)


@dataclass(frozen=True, slots=True)
class Pattern:
    name: str
    regex: re.Pattern[str]
    value_group: int = 0  # which group is the candidate secret (checked against the placeholder list)


PATTERNS: tuple[Pattern, ...] = (
    Pattern("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    Pattern("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    Pattern("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    Pattern("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    Pattern("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    Pattern(
        "credential in a URL",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s:/@]{6,})@[^\s/]+", re.IGNORECASE),
        value_group=1,
    ),
    Pattern(
        "secret assignment",
        re.compile(
            r"""(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b["']?\s*[:=]\s*["']?([A-Za-z0-9+/_.\-]{16,})"""
        ),
        value_group=1,
    ),
    Pattern("managed database host", re.compile(r"\b[a-z0-9-]+\.[a-z0-9]+\.[a-z0-9-]+\.rds\.amazonaws\.com\b")),
    Pattern("cloud account id in an ARN", re.compile(r"\barn:aws[a-z-]*:[a-z0-9-]+:[a-z0-9-]*:\d{12}:")),
)


def scan_text(text: str) -> list[tuple[int, str]]:
    """``(line, pattern name)`` for every non-placeholder match. The match itself is never returned."""
    hits: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern in PATTERNS:
            for match in pattern.regex.finditer(line):
                # Only the matched text decides: a real key on a line that happens to say "for example"
                # must still be reported.
                candidate = match.group(pattern.value_group)
                if _PLACEHOLDER.search(candidate) or candidate.lower() in _DEV_DEFAULTS:
                    continue
                hits.append((number, pattern.name))
    return hits


def _candidates(repo: Repo, config: Config) -> list[str]:
    paths = {"CLAUDE.md", "AGENTS.md"}
    for base in (config.docs_dir, ".claude"):
        root = repo.path(base)
        if root.is_dir():
            paths.update(
                p.relative_to(repo.root).as_posix()
                for p in root.rglob("*")
                if p.is_file() and p.suffix in SCANNED_SUFFIXES and p.stat().st_size <= MAX_BYTES
            )
    return sorted(p for p in paths if repo.path(p).is_file())


def _article(name: str) -> str:
    return "an" if name[0].lower() in "aeiou" else "a"


def no_secrets(repo: Repo, config: Config) -> RuleResult:
    rule = "no-secrets"
    files = _candidates(repo, config)
    findings = [
        Finding(
            rule,
            path,
            f"looks like {_article(name)} {name} (value not shown): remove it and rotate if it was ever real",
            line,
        )
        for path in files
        for line, name in scan_text(repo.read(path))
    ]
    return RuleResult(rule, len(files), tuple(findings))
