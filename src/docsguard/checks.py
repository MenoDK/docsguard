"""Runs the rules, applies the written exemptions, and renders the verdict."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from . import __version__
from .config import CONFIG_FILE, Config
from .model import Finding, RuleResult
from .repo import Repo
from .rules.adr import adr_rules
from .rules.budget import instruction_budget
from .rules.docs_map import claude_entrypoint, map_complete, map_counts, map_links_live
from .rules.handoff import handoff_rules
from .rules.secrets import no_secrets
from .rules.skills import skill_shape
from .rules.staged import same_commit

Rule = Callable[[Repo, Config], RuleResult]

# name -> (function, one-line statement of what a failure means)
RULES: dict[str, tuple[Rule, str]] = {
    "claude-entrypoint": (claude_entrypoint, "CLAUDE.md exists and points at the docs map"),
    "map-links-live": (map_links_live, "every link in the docs map resolves"),
    "map-complete": (map_complete, "every document under docs/ is reachable from the map"),
    "map-counts": (map_counts, "counts the map declares match the disk"),
    "adr-shape": (
        adr_rules,
        "ADRs have context, decision, rejected alternatives; numbering and index are whole",
    ),
    "handoff-shape": (handoff_rules, "the handoff has its eight sections, a date and a measured suite state"),
    "instruction-budget": (instruction_budget, "what a session loads at startup fits its budget"),
    "skill-shape": (
        skill_shape,
        "skills are discoverable (Use when…) and short enough to survive compaction",
    ),
    "no-secrets": (no_secrets, "no credentials or infrastructure identifiers in session-facing documents"),
}
STAGED_RULE = ("same-commit", (same_commit, "a new document is mapped in the commit that creates it"))


@dataclass(frozen=True, slots=True)
class Report:
    results: tuple[RuleResult, ...]

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.results for f in r.findings]

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)


def _apply_exemptions(results: list[RuleResult], config: Config) -> list[RuleResult]:
    if not config.exemptions:
        return results
    used: set[int] = set()
    filtered: list[RuleResult] = []
    for result in results:
        kept: list[Finding] = []
        for finding in result.findings:
            hit = next(
                (i for i, e in enumerate(config.exemptions) if e.rule == finding.rule and e.path == finding.path),
                None,
            )
            if hit is None:
                kept.append(finding)
            else:
                used.add(hit)
        filtered.append(RuleResult(result.rule, result.examined, tuple(kept), result.skipped))
    stale = [
        Finding(
            "exemptions",
            CONFIG_FILE,
            f"exemption for {e.rule} on {e.path} matches nothing any more: delete it",
        )
        for i, e in enumerate(config.exemptions)
        if i not in used
    ]
    filtered.append(RuleResult("exemptions", len(config.exemptions), tuple(stale)))
    return filtered


def run_checks(repo: Repo, config: Config, *, staged: bool = False, only: Iterable[str] | None = None) -> Report:
    catalogue = dict(RULES)
    if staged:
        catalogue[STAGED_RULE[0]] = STAGED_RULE[1]
    selected = list(only) if only else list(catalogue)
    unknown = [name for name in selected if name not in catalogue]
    if unknown:
        raise KeyError(f"unknown rule(s): {', '.join(unknown)}; known: {', '.join(catalogue)}")
    results = [catalogue[name][0](repo, config) for name in selected]
    return Report(tuple(_apply_exemptions(results, config) if not only else results))


def render(report: Report, root: str) -> str:
    lines = [f"docsguard {__version__}: {root}"]
    for r in report.results:
        if r.skipped:
            lines.append(f"  -  {r.rule:<20} skipped: {r.skipped}")
        elif r.vacuous:
            lines.append(f"  x  {r.rule:<20} examined nothing: a guard that sees nothing proves nothing")
        elif r.findings:
            lines.append(f"  x  {r.rule:<20} {r.examined} examined, {len(r.findings)} finding(s)")
        else:
            lines.append(f"  ok {r.rule:<20} {r.examined} examined")
        lines.extend(f"       {f.render()}" for f in r.findings)
    problems = len(report.findings) + sum(1 for r in report.results if r.vacuous)
    lines.append("OK" if report.ok else f"FAILED: {problems} problem(s)")
    return "\n".join(lines)
