"""Read-only view of the repository under inspection, plus the little markdown parsing the rules share."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_FENCE = re.compile(r"^\s*(```|~~~)")
_LINK = re.compile(r"(?<!\!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


@dataclass(frozen=True, slots=True)
class Link:
    target: str  # as written
    line: int


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    text: str
    line: int  # 1-based


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, rel: str) -> Path:
        return self.root / rel

    def exists(self, rel: str) -> bool:
        return self.path(rel).exists()

    def read(self, rel: str) -> str:
        return self.path(rel).read_text(encoding="utf-8", errors="replace")

    def markdown_under(self, rel_dir: str) -> list[str]:
        """Every ``.md`` below ``rel_dir`` (recursive), as sorted posix paths relative to the root."""
        base = self.path(rel_dir)
        if not base.is_dir():
            return []
        return sorted(p.relative_to(self.root).as_posix() for p in base.rglob("*.md") if p.is_file())

    def resolve_link(self, from_rel: str, target: str) -> str | None:
        """Where a relative link written in ``from_rel`` points, as a root-relative posix path.

        ``None`` for anything that is not a local file link (URLs, mail, pure anchors) and for links
        that climb out of the repository.
        """
        if not target or target.startswith(("#", "mailto:", "tel:")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            return None
        clean = target.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            return None
        base = PurePosixPath(from_rel).parent
        parts: list[str] = []
        for part in (base / clean).parts:
            if part in ("", "."):
                continue
            if part == "..":
                if not parts:
                    return None
                parts.pop()
            else:
                parts.append(part)
        return "/".join(parts)


def iter_prose_lines(text: str) -> Iterator[tuple[int, str]]:
    """``(1-based line number, line)`` for every line outside fenced code blocks."""
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def links(text: str) -> list[Link]:
    """Markdown links outside code fences. Inline code spans are skipped so examples do not count."""
    found: list[Link] = []
    for number, line in iter_prose_lines(text):
        stripped = re.sub(r"`[^`]*`", "", line)
        for match in _LINK.finditer(stripped):
            found.append(Link(target=match.group(1).strip("<>"), line=number))
    return found


def headings(text: str, level: int | None = None) -> list[Heading]:
    result: list[Heading] = []
    for number, line in iter_prose_lines(text):
        match = _HEADING.match(line)
        if match and (level is None or len(match.group(1)) == level):
            result.append(Heading(level=len(match.group(1)), text=match.group(2), line=number))
    return result


def section_body(text: str, heading: Heading) -> str:
    """Text under ``heading`` up to the next heading of the same or a higher level."""
    lines = text.splitlines()
    body: list[str] = []
    in_fence = False
    for index in range(heading.line, len(lines)):
        line = lines[index]
        if _FENCE.match(line):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line)
        if match and len(match.group(1)) <= heading.level:
            break
        body.append(line)
    return "\n".join(body).strip()


def front_matter(text: str) -> tuple[dict[str, str], str]:
    """Minimal YAML front matter: ``key: value`` pairs, optionally block scalars (``|`` / ``>``).

    Deliberately not a YAML parser. Anything nested is ignored rather than guessed at; the rules only
    need flat keys such as ``name``, ``description`` and ``paths``.
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].splitlines()
    body = text[end + 4 :].lstrip("\n")
    data: dict[str, str] = {}
    key: str | None = None
    block: list[str] = []
    folded = False

    def flush() -> None:
        nonlocal key, block
        if key is not None and block:
            data[key] = (" " if folded else "\n").join(s.strip() for s in block).strip()
        key, block = None, []

    for line in raw:
        top = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if top and not line.startswith((" ", "\t")):
            flush()
            value = top.group(2).strip()
            if value in ("|", ">", "|-", ">-"):
                key, folded = top.group(1), value.startswith(">")
            else:
                data[top.group(1)] = value.strip("\"'")
        elif key is not None:
            block.append(line)
    flush()
    return data, body
