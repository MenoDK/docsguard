"""Plain data shared by every rule. No behaviour here on purpose."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Finding:
    """One defect, accused at the granularity of the defect: a file (and a line when there is one)."""

    rule: str
    path: str  # repo-relative, always posix separators
    message: str
    line: int | None = None

    def render(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.rule}] {where}: {self.message}"


@dataclass(frozen=True, slots=True)
class RuleResult:
    """What a rule saw and what it found.

    ``examined`` exists to defeat vacuous passes: a guard that looked at zero items proves nothing, so
    ``check`` treats "examined nothing and was not explicitly skipped" as a failure of its own.
    """

    rule: str
    examined: int
    findings: tuple[Finding, ...] = ()
    skipped: str | None = None  # why the rule did not apply; shown to the reader, never silent

    @property
    def vacuous(self) -> bool:
        return self.skipped is None and self.examined == 0

    @property
    def ok(self) -> bool:
        return not self.findings and not self.vacuous
