"""The handoff: where a fresh session resumes from disk alone.

Eight sections, because each one answers a question a cold reader cannot recover from the code:
what is live, where work stopped, what the owner does now, deadlines, what NOT to do, which decisions
stand (with their ADRs), what was learned that is not in the code, and the suite state. The last one
must carry a measured number: "report what happened, not what was expected".
"""

from __future__ import annotations

import datetime
import re

from ..config import Config
from ..model import Finding, RuleResult
from ..repo import Repo, headings, links, section_body

# (label, pattern matched against the H2 text, lower-cased)
SECTIONS: tuple[tuple[str, str], ...] = (
    ("what is live", r"\blive\b"),
    ("where we stopped", r"stopped"),
    ("what the owner does now", r"\bowner\b"),
    ("deadlines", r"deadline"),
    ("what NOT to do", r"\bnot to do\b|\bdo not\b|\bdon'?t\b|\bwhat not\b"),
    ("decisions", r"decision"),
    ("learned, not in the code", r"learned|not in the code"),
    ("suite state", r"\bsuite\b|test state"),
)
_UPDATED = re.compile(r"^\W*updated\W*[:\-]\W*(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE | re.MULTILINE)


def handoff_rules(repo: Repo, config: Config) -> RuleResult:
    rule = "handoff-shape"
    if not config.handoff_file:
        return RuleResult(rule, 0, skipped="handoff disabled in config")
    if not repo.exists(config.handoff_file):
        return RuleResult(
            rule,
            1,
            (Finding(rule, config.handoff_file, "missing: a fresh session cannot resume from disk alone"),),
        )
    text = repo.read(config.handoff_file)
    path = config.handoff_file
    findings: list[Finding] = []

    stamp = _UPDATED.search(text)
    if not stamp:
        findings.append(Finding(rule, path, "has no 'Updated: YYYY-MM-DD' line"))
    else:
        try:
            datetime.date.fromisoformat(stamp.group(1))
        except ValueError:
            findings.append(Finding(rule, path, f"'Updated: {stamp.group(1)}' is not a real date"))

    h2 = headings(text, level=2)
    for label, pattern in SECTIONS:
        head = next((h for h in h2 if re.search(pattern, h.text.lower())), None)
        if head is None:
            findings.append(Finding(rule, path, f"is missing the section '{label}'"))
            continue
        body = section_body(text, head)
        if not body:
            findings.append(Finding(rule, path, f"section '{label}' is empty", head.line))
        elif label == "suite state" and not re.search(r"\d", body):
            findings.append(
                Finding(
                    rule,
                    path,
                    "section 'suite state' carries no number: report what ran, not what was expected",
                    head.line,
                )
            )
        elif label == "decisions" and repo.path(config.adr_dir).is_dir():
            cites_adr = any(
                (repo.resolve_link(path, link.target) or "").startswith(config.adr_dir.rstrip("/") + "/")
                for link in links(body)
            )
            if not cites_adr and not re.search(r"\bnone\b", body, re.IGNORECASE):
                findings.append(Finding(rule, path, "section 'decisions' cites no ADR (or says 'none')", head.line))
    return RuleResult(rule, len(SECTIONS), tuple(findings))
