"""The docs map: ``00-READ-FIRST.md`` is a *map, not content*.

Three guards keep it honest:

* ``map-complete``    every document under ``docs/`` is reachable from the map (a stale index is a defect);
* ``map-links-live``  every link in the map points at something that exists;
* ``map-counts``      numbers the map declares ("8 ADRs") are checked against the disk, not trusted.

Reachability follows links from the map, and descends only through index files (``README.md`` /
``index.md``). That lets the map point at ``docs/adr/README.md`` instead of listing forty records, while
still failing on an ADR the index forgot.
"""

from __future__ import annotations

import fnmatch
import re
from collections import deque

from ..config import Config
from ..model import Finding, RuleResult
from ..repo import Repo, iter_prose_lines, links

INDEX_NAMES = frozenset({"README.md", "index.md"})
_COUNT = re.compile(r"<!--\s*docsguard:count\s+(?P<attrs>[^>]*?)\s*-->")
_ATTR = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')


def _map_missing(config: Config, rule: str) -> RuleResult:
    return RuleResult(rule, examined=1, findings=(Finding(rule, config.map_file, "the docs map does not exist"),))


def map_links_live(repo: Repo, config: Config) -> RuleResult:
    rule = "map-links-live"
    if not repo.exists(config.map_file):
        return _map_missing(config, rule)
    findings: list[Finding] = []
    examined = 0
    for link in links(repo.read(config.map_file)):
        target = repo.resolve_link(config.map_file, link.target)
        if target is None:
            continue
        examined += 1
        if not repo.exists(target):
            findings.append(
                Finding(rule, config.map_file, f"links to '{link.target}', which does not exist", link.line)
            )
    return RuleResult(rule, examined, tuple(findings))


def _reachable(repo: Repo, config: Config) -> set[str]:
    seen = {config.map_file}
    queue: deque[str] = deque([config.map_file])
    while queue:
        current = queue.popleft()
        if not repo.exists(current):
            continue
        for link in links(repo.read(current)):
            target = repo.resolve_link(current, link.target)
            if target is None or target in seen or not target.endswith(".md") or not repo.exists(target):
                continue
            seen.add(target)
            # Only index files fan out: a normal document linking another does not make it "mapped".
            if target.rsplit("/", 1)[-1] in INDEX_NAMES:
                queue.append(target)
    return seen


def map_complete(repo: Repo, config: Config) -> RuleResult:
    rule = "map-complete"
    if not repo.exists(config.map_file):
        return _map_missing(config, rule)
    archived = tuple(d.rstrip("/") + "/" for d in config.archive_dirs)
    documents = [d for d in repo.markdown_under(config.docs_dir) if not d.startswith(archived)]
    reachable = _reachable(repo, config)
    findings = [
        Finding(
            rule,
            doc,
            f"not reachable from {config.map_file}: add it to the map in the same commit that creates it",
        )
        for doc in documents
        if doc not in reachable
    ]
    return RuleResult(rule, len(documents), tuple(findings))


def _attributes(raw: str) -> dict[str, str]:
    return {m.group(1): m.group(2) if m.group(2) is not None else m.group(3) for m in _ATTR.finditer(raw)}


def map_counts(repo: Repo, config: Config) -> RuleResult:
    """``<!-- docsguard:count dir=docs/adr glob=0*.md expect=8 -->`` is verified against the file system."""
    rule = "map-counts"
    if not repo.exists(config.map_file):
        return _map_missing(config, rule)
    findings: list[Finding] = []
    examined = 0
    text = repo.read(config.map_file)
    for number, line in iter_prose_lines(text):
        for match in _COUNT.finditer(line):
            examined += 1
            attrs = _attributes(match.group("attrs"))
            missing = [key for key in ("dir", "expect") if key not in attrs]
            if missing or not attrs.get("expect", "").isdigit():
                findings.append(
                    Finding(rule, config.map_file, "count marker needs dir=… and a numeric expect=…", number)
                )
                continue
            pattern = attrs.get("glob", "*")
            base = repo.path(attrs["dir"])
            actual = (
                sum(1 for p in base.iterdir() if p.is_file() and fnmatch.fnmatch(p.name, pattern))
                if base.is_dir()
                else 0
            )
            if actual != int(attrs["expect"]):
                findings.append(
                    Finding(
                        rule,
                        config.map_file,
                        f"declares {attrs['expect']} file(s) matching '{pattern}' in {attrs['dir']}, "
                        f"the disk has {actual}",
                        number,
                    )
                )
    if examined == 0:
        return RuleResult(rule, 0, skipped="the map declares no counts")
    return RuleResult(rule, examined, tuple(findings))


def claude_entrypoint(repo: Repo, config: Config) -> RuleResult:
    """``CLAUDE.md`` exists and points at the map: the map is the source, CLAUDE.md only mirrors it."""
    rule = "claude-entrypoint"
    if not repo.exists("CLAUDE.md"):
        return RuleResult(rule, 1, (Finding(rule, "CLAUDE.md", "missing: a session has no entry point"),))
    if config.map_file not in repo.read("CLAUDE.md"):
        return RuleResult(rule, 1, (Finding(rule, "CLAUDE.md", f"does not point at the docs map ({config.map_file})"),))
    return RuleResult(rule, 1)
