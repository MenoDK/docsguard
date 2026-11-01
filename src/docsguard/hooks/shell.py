"""A small, honest shell command analyser for hooks.

It answers one question: *which simple commands does this string run?* It understands quoting, the
separators ``; & | && ||`` and newlines, ``$( )`` and backtick substitutions, here-documents, and the
wrappers people put in front of a command (``sudo``, ``env``, ``timeout`` …, ``bash -c '…'``, ``eval``).

It is **not** a shell and not a security boundary: a determined author can always obfuscate (variables,
``base64 | sh``, aliases). Hooks like these stop *accidents*: the 2 a.m. ``reset --hard`` that nobody
meant. They fail toward allowing what they cannot parse; the limits are documented in the README.
"""

from __future__ import annotations

import posixpath
import re
import shlex
from collections.abc import Iterator

MAX_DEPTH = 6
_HEREDOC = re.compile(r"<<(-?)\s*(?:'([^']+)'|\"([^\"]+)\"|\\?([A-Za-z_][A-Za-z0-9_]*))")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
KEYWORDS = frozenset(
    {
        "then",
        "do",
        "else",
        "elif",
        "if",
        "while",
        "until",
        "!",
        "{",
        "time",
        "command",
        "exec",
        "builtin",
        "nohup",
        "setsid",
    }
)
# wrapper -> options that consume the next token as their value
WRAPPERS: dict[str, frozenset[str]] = {
    "sudo": frozenset({"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U", "-r", "-t"}),
    "doas": frozenset({"-u", "-C"}),
    "env": frozenset({"-u", "-C", "-S"}),
    "nice": frozenset({"-n"}),
    "ionice": frozenset({"-c", "-n", "-p"}),
    "timeout": frozenset({"-s", "-k"}),
    "xargs": frozenset({"-I", "-n", "-P", "-L", "-d", "-E", "-s", "-a"}),
    "stdbuf": frozenset(),
}


def scan(command: str) -> tuple[list[str], list[str]]:
    """Split ``command`` into top-level simple commands and the bodies of nested substitutions."""
    segments: list[str] = []
    nested: list[str] = []
    buf: list[str] = []
    pending: list[tuple[str, bool]] = []  # here-doc delimiters waiting for the next newline
    quote: str | None = None
    i, n = 0, len(command)

    def flush() -> None:
        text = "".join(buf).strip()
        if text:
            segments.append(text)
        buf.clear()

    while i < n:
        c = command[i]
        if quote == "'":
            buf.append(c)
            quote = None if c == "'" else quote
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            buf.append(command[i : i + 2])
            i += 2
            continue
        if c == "$" and command.startswith("$(", i):
            inner, end = _balanced(command, i + 2)
            nested.append(inner)
            buf.append(" ")
            i = end + 1
            continue
        if c == "`":
            end = _closing_backtick(command, i + 1)
            nested.append(command[i + 1 : end])
            buf.append(" ")
            i = end + 1
            continue
        if quote == '"':
            buf.append(c)
            quote = None if c == '"' else quote
            i += 1
            continue
        if c in "'\"":
            quote = c
            buf.append(c)
            i += 1
            continue
        if command.startswith("<<", i) and not command.startswith("<<<", i):
            match = _HEREDOC.match(command, i)
            if match:
                delimiter = match.group(2) or match.group(3) or match.group(4)
                pending.append((delimiter, match.group(1) == "-"))
                buf.append(command[i : match.end()])
                i = match.end()
                continue
        if c == "\n":
            flush()
            i += 1
            if pending:
                i = _skip_heredocs(command, i, pending)
                pending.clear()
            continue
        if c in ";&|()":
            flush()
            i += 1
            continue
        buf.append(c)
        i += 1
    flush()
    return segments, nested


def _balanced(text: str, start: int) -> tuple[str, int]:
    """Body and closing index of a ``$( … )`` that starts at ``start`` (just after the opening)."""
    depth, i, quote = 1, start, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
        elif c == "\\":
            i += 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i], i
        i += 1
    return text[start:], len(text)


def _closing_backtick(text: str, start: int) -> int:
    i = start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "`":
            return i
        i += 1
    return len(text)


def _skip_heredocs(text: str, i: int, pending: list[tuple[str, bool]]) -> int:
    for delimiter, strip_tabs in pending:
        while i < len(text):
            end = text.find("\n", i)
            line = text[i : end if end != -1 else len(text)]
            i = len(text) if end == -1 else end + 1
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                break
    return i


def words(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:  # unbalanced quote: examine what is there rather than ignore it
        return segment.split()


def strip_wrappers(tokens: list[str]) -> list[str]:
    """Drop leading assignments, shell keywords and wrappers so ``tokens[0]`` is the real command."""
    while tokens:
        head = tokens[0]
        if _ASSIGNMENT.match(head) or head in KEYWORDS:
            tokens = tokens[1:]
            continue
        wrapper = WRAPPERS.get(posixpath.basename(head))
        if wrapper is None:
            break
        tokens = _skip_wrapper_options(posixpath.basename(head), tokens[1:], wrapper)
    return tokens


def _skip_wrapper_options(name: str, tokens: list[str], value_options: frozenset[str]) -> list[str]:
    i = 0
    while i < len(tokens):
        word = tokens[i]
        if word == "--":
            i += 1
            break
        if word.startswith("-") and len(word) > 1:
            i += 2 if word in value_options else 1
            continue
        if name == "env" and _ASSIGNMENT.match(word):
            i += 1
            continue
        break
    rest = tokens[i:]
    if name in ("timeout", "nice") and rest and re.fullmatch(r"[0-9.]+[smhd]?", rest[0]):
        rest = rest[1:]  # the duration / niceness operand
    return rest


def simple_commands(command: str, _depth: int = 0) -> Iterator[list[str]]:
    """Every simple command (wrapper-stripped token list), recursing into substitutions, ``bash -c`` and ``eval``."""
    if _depth > MAX_DEPTH:
        return
    segments, nested = scan(command)
    for inner in nested:
        yield from simple_commands(inner, _depth + 1)
    for segment in segments:
        tokens = strip_wrappers(words(segment))
        if not tokens:
            continue
        name = posixpath.basename(tokens[0])
        if name in SHELLS:
            script = _dash_c_script(tokens[1:])
            if script is not None:
                yield from simple_commands(script, _depth + 1)
                continue
        if name == "eval":
            yield from simple_commands(" ".join(tokens[1:]), _depth + 1)
            continue
        yield tokens


def _dash_c_script(args: list[str]) -> str | None:
    for index, arg in enumerate(args):
        if arg.startswith("-") and not arg.startswith("--") and "c" in arg[1:]:
            return args[index + 1] if index + 1 < len(args) else None
        if not arg.startswith("-"):
            return None
    return None
