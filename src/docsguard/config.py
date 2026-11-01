"""``docsguard.toml``: optional, strict, and every dismissal carries a written reason.

Unknown keys are an error rather than a silent no-op: a typo in a guard's config that quietly turns the
guard off is the worst way for a guard to fail.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_FILE = "docsguard.toml"
MIN_REASON_CHARS = 10


class ConfigError(ValueError):
    """The configuration is invalid. Raised, never swallowed."""


@dataclass(frozen=True, slots=True)
class Exemption:
    rule: str
    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class ProtectedPath:
    pattern: str
    reason: str


@dataclass(frozen=True, slots=True)
class Config:
    docs_dir: str = "docs"
    map_file: str = "docs/00-READ-FIRST.md"
    adr_dir: str = "docs/adr"
    handoff_file: str = "docs/HANDOFF.md"
    skills_dir: str = ".claude/skills"
    archive_dirs: tuple[str, ...] = ("docs/archive",)
    max_lines_per_file: int = 200
    max_session_tokens: int = 6000
    max_skill_tokens: int = 5000
    exemptions: tuple[Exemption, ...] = ()
    protected: tuple[ProtectedPath, ...] = ()
    extend_default_protected: bool = True
    authorizations_file: str = ".claude/authorizations.txt"


_TOP_STR = {"docs_dir", "map_file", "adr_dir", "handoff_file", "skills_dir", "authorizations_file"}
_BUDGET = {"max_lines_per_file", "max_session_tokens", "max_skill_tokens"}


def _expect(table: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {', '.join(unknown)}; allowed: {', '.join(sorted(allowed))}")


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{where} must be a string")
    return value


def _positive_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{where} must be a positive integer")
    return value


def parse(data: dict[str, Any]) -> Config:
    allowed = _TOP_STR | {"archive_dirs", "budget", "exempt", "scope"}
    _expect(data, allowed, "docsguard.toml")
    values: dict[str, Any] = {key: _string(data[key], key) for key in _TOP_STR if key in data}

    if "archive_dirs" in data:
        raw = data["archive_dirs"]
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise ConfigError("archive_dirs must be a list of strings")
        values["archive_dirs"] = tuple(raw)

    budget = data.get("budget", {})
    if not isinstance(budget, dict):
        raise ConfigError("[budget] must be a table")
    _expect(budget, _BUDGET, "[budget]")
    for key in _BUDGET & set(budget):
        values[key] = _positive_int(budget[key], f"[budget] {key}")

    exemptions: list[Exemption] = []
    for index, item in enumerate(data.get("exempt", []), start=1):
        where = f"[[exempt]] #{index}"
        if not isinstance(item, dict):
            raise ConfigError(f"{where} must be a table")
        _expect(item, {"rule", "path", "reason"}, where)
        reason = _string(item.get("reason", ""), f"{where} reason").strip()
        if len(reason) < MIN_REASON_CHARS:
            raise ConfigError(f"{where}: a dismissal needs a written reason (at least {MIN_REASON_CHARS} characters)")
        exemptions.append(
            Exemption(
                _string(item.get("rule", ""), f"{where} rule"),
                _string(item.get("path", ""), f"{where} path"),
                reason,
            )
        )
    values["exemptions"] = tuple(exemptions)

    scope = data.get("scope", {})
    if not isinstance(scope, dict):
        raise ConfigError("[scope] must be a table")
    _expect(scope, {"protected", "extend_defaults"}, "[scope]")
    protected: list[ProtectedPath] = []
    for index, item in enumerate(scope.get("protected", []), start=1):
        where = f"[[scope.protected]] #{index}"
        if not isinstance(item, dict):
            raise ConfigError(f"{where} must be a table")
        _expect(item, {"pattern", "reason"}, where)
        reason = _string(item.get("reason", ""), f"{where} reason").strip()
        if len(reason) < MIN_REASON_CHARS:
            raise ConfigError(
                f"{where}: a protected path needs the reason it is protected (at least {MIN_REASON_CHARS} characters)"
            )
        protected.append(ProtectedPath(_string(item.get("pattern", ""), f"{where} pattern"), reason))
    values["protected"] = tuple(protected)
    if "extend_defaults" in scope:
        if not isinstance(scope["extend_defaults"], bool):
            raise ConfigError("[scope] extend_defaults must be true or false")
        values["extend_default_protected"] = scope["extend_defaults"]
    return Config(**values)


def load(root: Path) -> Config:
    path = root / CONFIG_FILE
    if not path.is_file():
        return Config()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{CONFIG_FILE}: {error}") from error
    return parse(data)
