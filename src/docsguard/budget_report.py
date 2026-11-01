"""``docsguard budget``: what a session pays up front, against what reading everything would cost.

The point of the docs map is progressive disclosure. This report puts a number on it for *this*
repository, measured, so the claim "a fresh session needs ~2k tokens, not ~30k" is checkable.
All figures are estimates (see ``tokens.py``).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .config import Config
from .repo import Repo
from .rules.budget import session_set
from .tokens import estimate_tokens


def build(repo: Repo, config: Config) -> dict[str, Any]:
    loaded = session_set(repo)
    paid = {f.path for f in loaded}
    archived = tuple(d.rstrip("/") + "/" for d in config.archive_dirs)
    on_demand = sorted(
        (
            (doc, estimate_tokens(repo.read(doc)))
            for doc in repo.markdown_under(config.docs_dir)
            if doc not in paid and not doc.startswith(archived)
        ),
        key=lambda item: (-item[1], item[0]),
    )
    session_tokens = sum(f.tokens for f in loaded)
    everything = session_tokens + sum(tokens for _, tokens in on_demand)
    # A real session also opens the map and, when resuming, the handoff: say so rather than flatter the number.
    typical = session_tokens + sum(t for path, t in on_demand if path in (config.map_file, config.handoff_file))
    return {
        "session_start": [asdict(f) for f in loaded],
        "session_tokens": session_tokens,
        "session_budget": config.max_session_tokens,
        "on_demand": [{"path": path, "tokens": tokens} for path, tokens in on_demand],
        "typical_start_tokens": typical,
        "everything_tokens": everything,
        "saving_percent": round(100 * (1 - typical / everything), 1) if everything else 0.0,
        "estimate": "characters / 4: good for budgeting, not for billing",
    }


def render(data: dict[str, Any]) -> str:
    shown = data["on_demand"][:15]
    paths = [f["path"] for f in data["session_start"]] + [i["path"] for i in shown]
    width = max([len("total"), *map(len, paths)])
    lines = ["Session start: paid on every session"]
    for f in data["session_start"]:
        lines.append(f"  {f['path']:<{width}} {f['lines']:>4} lines  ~{f['tokens']:>6,} tokens  ({f['via']})")
    lines.append(
        f"  {'total':<{width}} {'':>10}  ~{data['session_tokens']:>6,} tokens  (budget {data['session_budget']:,})"
    )
    lines.append("")
    lines.append("On demand: opened through the map, paid only when needed")
    for item in shown:
        lines.append(f"  {item['path']:<{width}} {'':>10}  ~{item['tokens']:>6,} tokens")
    if len(data["on_demand"]) > len(shown):
        lines.append(f"  … and {len(data['on_demand']) - len(shown)} more")
    lines.append("")
    lines.append(
        f"A typical start (the above, plus the map and the handoff): ~{data['typical_start_tokens']:,} tokens."
    )
    lines.append(
        f"Reading every document instead: ~{data['everything_tokens']:,} tokens; "
        f"a typical start is {100 - data['saving_percent']:.1f}% of that."
    )
    lines.append(f"({data['estimate']})")
    return "\n".join(lines)
