"""Skills: small, triggerable, and short enough to survive compaction.

After a conversation is compacted, skill bodies are truncated, so the instructions that matter must fit
and sit early. The guard checks the shape that makes a skill discoverable and bounded: a name that
matches its directory, a description that says *when* to use it, and a body under the token cap.
"""

from __future__ import annotations

import re

from ..config import Config
from ..model import Finding, RuleResult
from ..repo import Repo, front_matter
from ..tokens import estimate_tokens

_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_DESCRIPTION_CHARS = 1024


def skill_shape(repo: Repo, config: Config) -> RuleResult:
    rule = "skill-shape"
    base = config.skills_dir.rstrip("/")
    if not repo.path(base).is_dir():
        return RuleResult(rule, 0, skipped=f"no {base} directory")
    skills = sorted(d.name for d in repo.path(base).iterdir() if d.is_dir())
    findings: list[Finding] = []
    for name in skills:
        path = f"{base}/{name}/SKILL.md"
        if not repo.exists(path):
            findings.append(Finding(rule, f"{base}/{name}/", "has no SKILL.md"))
            continue
        text = repo.read(path)
        meta, body = front_matter(text)
        if not meta:
            findings.append(Finding(rule, path, "has no front matter (name, description)"))
            continue
        if meta.get("name") != name or not _NAME.match(name):
            findings.append(
                Finding(
                    rule,
                    path,
                    f"front matter name '{meta.get('name')}' must equal the directory '{name}' (kebab-case)",
                )
            )
        description = meta.get("description", "")
        raw = re.search(r"^description:[ \t]*(?P<value>\S.*)$", text, re.MULTILINE)
        if (
            raw
            and not raw.group("value").startswith(("'", '"', "|", ">"))
            and re.search(r":\s|\s#", raw.group("value"))
        ):
            findings.append(
                Finding(
                    rule, path, "description has an unquoted ': ' or ' #': YAML will mis-read it. Quote it or reword"
                )
            )
        if not description:
            findings.append(
                Finding(rule, path, "has no description: the model decides whether to load a skill from it")
            )
        elif "use when" not in description.lower():
            findings.append(
                Finding(
                    rule,
                    path,
                    "description does not say 'Use when …': say when it triggers, not only what it is",
                )
            )
        elif len(description) > MAX_DESCRIPTION_CHARS:
            findings.append(
                Finding(rule, path, f"description is {len(description)} chars, over {MAX_DESCRIPTION_CHARS}")
            )
        tokens = estimate_tokens(body)
        if tokens > config.max_skill_tokens:
            findings.append(
                Finding(
                    rule,
                    path,
                    f"body is ~{tokens} tokens, over {config.max_skill_tokens}: it will be truncated after compaction",
                )
            )
    return RuleResult(rule, len(skills), tuple(findings))
