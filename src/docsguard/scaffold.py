"""``docsguard init``: copy the template into a repository.

The template is validated by construction: the test-suite initialises one and requires ``check`` to
pass on it. A template that fails its own guards teaches the wrong lesson.
"""

from __future__ import annotations

import datetime
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

TEXT_SUFFIXES = {".md", ".json", ".toml", ".txt", ".yml", ".yaml", ""}


def _installed_name(name: str) -> str:
    """``dot-claude`` in the package becomes ``.claude`` on disk: build tools skip hidden directories."""
    return "." + name[4:] if name.startswith("dot-") else name


def _walk(node: Traversable, prefix: str = "") -> list[tuple[str, Traversable]]:
    found: list[tuple[str, Traversable]] = []
    for child in sorted(node.iterdir(), key=lambda c: c.name):
        path = f"{prefix}{_installed_name(child.name)}"
        if child.is_dir():
            found.extend(_walk(child, path + "/"))
        else:
            found.append((path, child))
    return found


def init(target: Path, project: str, *, force: bool = False) -> tuple[list[str], list[str]]:
    """Returns ``(created, skipped)``. Existing files are left alone unless ``force``."""
    created: list[str] = []
    skipped: list[str] = []
    today = datetime.date.today().isoformat()
    for relative, source in _walk(resources.files("docsguard") / "template"):
        destination = target / relative
        if destination.exists() and not force:
            skipped.append(relative)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        if Path(relative).suffix in TEXT_SUFFIXES:
            data = data.decode("utf-8").replace("{{project}}", project).replace("{{date}}", today).encode("utf-8")
        destination.write_bytes(data)
        created.append(relative)
    return created, skipped
