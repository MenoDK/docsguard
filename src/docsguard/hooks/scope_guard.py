"""Keep an AI session out of the places it must not write, unless a human wrote down why it may.

* **Reads are never blocked.** Reading a protected file is how you find out what is wrong with it.
* **Writes to protected paths are denied**, with the reason the path is protected.
* **Authorization is a line in a file that shows up in the diff:** ``path:<substring> -- <reason>`` in
  ``.claude/authorizations.txt``. A conversation can be forgotten; a committed line is reviewed. A line
  without a reason is ignored (and the denial says so), because an unexplained exception is how
  exceptions become the rule.
* **A denylist, not an allowlist.** An allowlist blocks every new, legitimate file until someone edits
  the list, and the first time that happens the hook is switched off.
"""

from __future__ import annotations

import os
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from ..config import Config, ProtectedPath
from ..config import load as load_config
from .protocol import Decision, emit_deny, read_payload, tool_input
from .shell import simple_commands

DEFAULT_PROTECTED: tuple[ProtectedPath, ...] = (
    ProtectedPath(".env", "environment files hold real credentials; edit .env.example instead"),
    ProtectedPath(".env.*", "environment files hold real credentials; edit .env.example instead"),
    ProtectedPath("**/*.pem", "private keys and certificates are never edited by a session"),
    ProtectedPath("**/*.key", "private keys and certificates are never edited by a session"),
    ProtectedPath("**/*.p12", "private keys and certificates are never edited by a session"),
    ProtectedPath("**/id_rsa*", "SSH keys are never edited by a session"),
    ProtectedPath("**/id_ed25519*", "SSH keys are never edited by a session"),
    ProtectedPath("**/.ssh/**", "SSH configuration and keys are never edited by a session"),
    ProtectedPath("**/.aws/credentials", "cloud credentials are never edited by a session"),
    ProtectedPath(".git/**", "git internals are changed with git, not with a file editor"),
)
ALLOWED_EXCEPTIONS = (".env.example", ".env.sample", ".env.template")
EDIT_TOOLS = {
    "Edit": "file_path",
    "Write": "file_path",
    "MultiEdit": "file_path",
    "NotebookEdit": "notebook_path",
}
_AUTHORIZATION = re.compile(r"^path:(?P<needle>\S+)\s+--\s+(?P<reason>\S.*)$")


@dataclass(frozen=True, slots=True)
class Authorizations:
    needles: tuple[str, ...]
    ignored: tuple[str, ...]  # lines that looked like authorizations but gave no reason


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """``**`` crosses directories, ``*`` and ``?`` do not; a pattern without ``/`` matches at any depth."""
    anchored = "/" in pattern
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    body = "".join(out)
    return re.compile(rf"^{body}$" if anchored else rf"^(?:.*/)?{body}$")


def load_authorizations(root: Path, config: Config) -> Authorizations:
    path = root / config.authorizations_file
    if not path.is_file():
        return Authorizations((), ())
    needles: list[str] = []
    ignored: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _AUTHORIZATION.match(line)
        if match:
            needles.append(match.group("needle"))
        elif line.startswith("path:"):
            ignored.append(line)
    return Authorizations(tuple(needles), tuple(ignored))


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / ".git").exists()
            or (candidate / ".claude").is_dir()
            or (candidate / "docsguard.toml").is_file()
        ):
            return candidate
    return start


def normalise(target: str, root: Path, cwd: Path) -> tuple[str, str]:
    """``(root-relative posix path, absolute posix path)`` with ``..`` and symlinks resolved."""
    expanded = os.path.expanduser(target)
    absolute = Path(expanded) if os.path.isabs(expanded) else cwd / expanded
    resolved = Path(os.path.realpath(absolute))
    try:
        relative = resolved.relative_to(os.path.realpath(root)).as_posix()
    except ValueError:
        relative = resolved.as_posix().lstrip("/")
    return relative, resolved.as_posix()


def protected_reason(relative: str, absolute: str, config: Config) -> str | None:
    if posixpath.basename(relative) in ALLOWED_EXCEPTIONS:
        return None
    rules = (*config.protected, *(DEFAULT_PROTECTED if config.extend_default_protected else ()))
    for rule in rules:
        regex = glob_to_regex(rule.pattern)
        if regex.match(relative) or regex.match(absolute.lstrip("/")):
            return f"'{rule.pattern}': {rule.reason}"
    return None


def written_paths(command: str) -> list[str]:
    """Best-effort: the files a shell command writes or deletes (redirections, tee, rm, mv, cp, sed -i …)."""
    targets: list[str] = []
    for tokens in simple_commands(command):
        name = posixpath.basename(tokens[0])
        args = tokens[1:]
        for index, token in enumerate(tokens):
            match = re.match(r"^\d*>>?\|?(.*)$", token)
            if match:
                target = match.group(1) or (tokens[index + 1] if index + 1 < len(tokens) else "")
                if target and not target.startswith("&") and target != "/dev/null":
                    targets.append(target)
        operands = [a for a in args if not a.startswith("-") and not re.match(r"^\d*>", a)]
        if name in ("tee", "rm", "unlink", "truncate", "shred", "touch", "chmod", "chown"):
            targets.extend(operands)
        elif name in ("mv", "cp", "install", "ln"):
            targets.extend(operands if name == "mv" else operands[-1:])
        elif name in ("sed", "perl") and any(a.startswith("-i") or a == "--in-place" for a in args):
            targets.extend(operands[1:] if name == "sed" else operands)
        elif name == "dd":
            targets.extend(a[3:] for a in args if a.startswith("of="))
    return targets


def evaluate(payload: dict[str, Any], root: Path, config: Config) -> Decision | None:
    cwd = Path(payload["cwd"]) if isinstance(payload.get("cwd"), str) else root
    data = tool_input(payload)
    tool = payload.get("tool_name")
    if tool in EDIT_TOOLS:
        raw = data.get(EDIT_TOOLS[str(tool)])
        candidates = [raw] if isinstance(raw, str) else []
    elif tool == "Bash" and isinstance(data.get("command"), str):
        candidates = written_paths(data["command"])
    else:
        return None

    authorizations = load_authorizations(root, config)
    for candidate in candidates:
        relative, absolute = normalise(candidate, root, cwd)
        reason = protected_reason(relative, absolute, config)
        if reason is None:
            continue
        if any(needle in relative or needle in absolute for needle in authorizations.needles):
            continue
        hint = (
            f"To allow it, a human adds the line `path:{relative} -- <why>` to {config.authorizations_file} "
            "and commits it, so the exception is reviewed."
        )
        if authorizations.ignored:
            hint += f" ({len(authorizations.ignored)} authorization line(s) were ignored because they give no reason.)"
        return Decision("protected-path", f"writing {relative} is blocked by {reason}. {hint}")
    return None


def run(stdin: TextIO, stdout: TextIO) -> int:
    payload = read_payload(stdin)
    if not payload:
        return 0
    start = Path(payload["cwd"]) if isinstance(payload.get("cwd"), str) else Path.cwd()
    root = find_root(start.resolve())
    decision = evaluate(payload, root, load_config(root))
    if decision:
        emit_deny(stdout, decision)
    return 0


__all__ = ["DEFAULT_PROTECTED", "evaluate", "glob_to_regex", "run", "written_paths"]
