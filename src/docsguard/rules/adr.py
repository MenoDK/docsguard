"""ADRs: the *why*, written before the code, with the alternatives that lost.

An ADR without a rejected alternative is a changelog entry. The rule therefore demands, per record:
a title, a status, a context, a decision, and at least one rejected alternative with a reason.
Numbering must be unique and gapless, and the index must list every record (checked, not trusted).
"""

from __future__ import annotations

import re

from ..config import Config
from ..model import Finding, RuleResult
from ..repo import Heading, Repo, headings, links, section_body

STATUSES = ("Proposed", "Accepted", "Superseded", "Deprecated", "Rejected")
_NAME = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
_STATUS = re.compile(rf"^\W*status\W*[:\-]?\W*({'|'.join(STATUSES)})\b(?P<rest>.*)$", re.IGNORECASE)
_SUPERSEDED_BY = re.compile(r"(?:ADR[-\s]?|\b)(\d{4})\b")
MIN_REJECTED_CHARS = 20


def _find(heads: list[Heading], word: str) -> Heading | None:
    return next((h for h in heads if h.level == 2 and word in h.text.lower()), None)


def _status_line(text: str) -> tuple[int, str, str] | None:
    for number, line in enumerate(text.splitlines(), start=1):
        match = _STATUS.match(line.strip())
        if match:
            return number, match.group(1).capitalize(), match.group("rest")
    return None


def adr_rules(repo: Repo, config: Config) -> RuleResult:
    rule = "adr-shape"
    if not repo.path(config.adr_dir).is_dir():
        return RuleResult(rule, 0, skipped=f"no {config.adr_dir} directory")

    findings: list[Finding] = []
    records: dict[int, str] = {}
    base = config.adr_dir.rstrip("/")
    for doc in repo.markdown_under(base):
        name = doc.rsplit("/", 1)[-1]
        if doc != f"{base}/{name}" or name == "README.md":
            continue
        match = _NAME.match(name)
        if not match:
            findings.append(Finding(rule, doc, "file name must look like 0007-short-kebab-title.md"))
            continue
        number = int(match.group(1))
        if number in records:
            findings.append(Finding(rule, doc, f"number {number:04d} is already used by {records[number]}"))
            continue
        records[number] = doc

    for doc in (records[n] for n in sorted(records)):
        findings.extend(_check_record(repo, doc, set(records)))

    if records:
        expected = set(range(1, max(records) + 1))
        for missing in sorted(expected - set(records)):
            findings.append(Finding(rule, f"{base}/", f"numbering has a gap: {missing:04d} is missing"))

    index = f"{base}/README.md"
    if not repo.exists(index):
        findings.append(Finding(rule, index, "the ADR index is missing"))
    else:
        indexed = {repo.resolve_link(index, link.target) for link in links(repo.read(index))}
        findings.extend(
            Finding(rule, doc, f"is not listed in {index}") for doc in records.values() if doc not in indexed
        )
    return RuleResult(rule, len(records), tuple(findings))


def _check_record(repo: Repo, doc: str, numbers: set[int]) -> list[Finding]:
    rule = "adr-shape"
    text = repo.read(doc)
    found: list[Finding] = []
    heads = headings(text)

    if not any(h.level == 1 for h in heads):
        found.append(Finding(rule, doc, "has no '# Title' heading"))

    status = _status_line(text)
    if status is None:
        found.append(Finding(rule, doc, f"has no 'Status:' line ({' / '.join(STATUSES)})"))
    elif status[1] == "Superseded":
        target = _SUPERSEDED_BY.search(status[2])
        if not target:
            found.append(Finding(rule, doc, "is Superseded but does not say by which ADR (number)", status[0]))
        elif int(target.group(1)) not in numbers:
            found.append(Finding(rule, doc, f"is superseded by {target.group(1)}, which does not exist", status[0]))

    for word, label in (("context", "Context"), ("decision", "Decision")):
        head = _find(heads, word)
        if head is None:
            found.append(Finding(rule, doc, f"has no '## {label}' section"))
        elif not section_body(text, head):
            found.append(Finding(rule, doc, f"'## {label}' is empty", head.line))

    rejected = _find(heads, "rejected")
    if rejected is None:
        found.append(Finding(rule, doc, "has no '## Rejected alternatives' section: an ADR records what lost, and why"))
    elif len(section_body(text, rejected)) < MIN_REJECTED_CHARS:
        found.append(Finding(rule, doc, "'## Rejected alternatives' names no alternative with a reason", rejected.line))
    return found
