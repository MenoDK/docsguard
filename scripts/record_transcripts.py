"""Records the output shown in the landing page's tour by running the REAL command line on the sample project.

Nothing on that page is typed by hand. Each transcript calls ``docsguard.cli.main`` (what the ``docsguard`` command
runs) or feeds a hook the JSON Claude Code would send, and keeps what was printed. The only edit is the temporary
directory's path, which becomes ``/work/sample-shop`` so a recording does not depend on where it ran.

    python scripts/record_transcripts.py            write site/transcripts.js
    python scripts/record_transcripts.py --check    record again and fail if site/transcripts.js no longer matches
"""

from __future__ import annotations

import contextlib
import html
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playground.lab import LABEL, Lab  # noqa: E402

from docsguard import cli  # noqa: E402

OUT = ROOT / "site" / "transcripts.js"
HEADER = (
    "/* Recorded from the real command line by scripts/record_transcripts.py. "
    "Do not edit: CI records again and compares. */\n"
)


class Tape:
    """Lines of a transcript. The kit inserts it as HTML, so every character is escaped when it is rendered."""

    def __init__(self, lab: Lab) -> None:
        self.lab = lab
        self.entries: list[tuple[str, str]] = []

    def say(self, text: str) -> None:
        if self.entries:
            self.entries.append(("", ""))
        self.entries.append(("tok-dim", f"# {text}"))

    def _clean(self, text: str) -> str:
        for path in {str(self.lab.root), str(self.lab.root.resolve())}:
            text = text.replace(path, LABEL)
        return text

    def run(self, shown: str, argv: list[str], stdin: str | None = None) -> None:
        """Run the real command line and print what it printed, line by line, coloured by what the line says."""
        self.entries.append(("tok-k", f"$ {shown}"))
        stdout = io.StringIO()
        saved = sys.stdin
        try:
            if stdin is not None:
                sys.stdin = io.StringIO(stdin)
            with contextlib.redirect_stdout(stdout):
                cli.main(argv)
        finally:
            sys.stdin = saved
        text = self._clean(stdout.getvalue()).rstrip("\n")
        if not text:
            self.entries.append(("tok-dim", "(nothing is printed: the tool call goes ahead)"))
            return
        for line in text.split("\n"):
            self.entries.append((self._colour(line), line))

    @staticmethod
    def _colour(line: str) -> str:
        if re.match(r"^\s+ok\s", line) or line == "OK":
            return "tok-ok"
        if re.match(r"^\s+x\s", line) or line.startswith("FAILED") or '"permissionDecision": "deny"' in line:
            return "tok-bad"
        return ""

    def render(self) -> str:
        out = []
        for cls, text in self.entries:
            shown = html.escape(text, quote=True)
            out.append(f'<span class="{cls}">{shown}</span>' if cls else shown)
        return "\n".join(out)


def check(tape: Tape, *rules: str) -> None:
    argv = ["check", "--root", str(tape.lab.root)]
    shown = "docsguard check"
    for rule in rules:
        argv += ["--rule", rule]
        shown += f" --rule {rule}"
    tape.run(shown, argv)


def hook(tape: Tape, which: str, payload: dict[str, object], *, with_cwd: bool = False) -> None:
    """The scope hook finds the project from the cwd in the payload: shown as a label, sent as the real one."""
    shown = {**payload, "cwd": LABEL} if with_cwd else payload
    real = {**payload, "cwd": str(tape.lab.root)} if with_cwd else payload
    tape.run(
        f"echo '{json.dumps(shown, separators=(',', ':'))}' | docsguard hook {which}",
        ["hook", which],
        stdin=json.dumps(real),
    )


def bash(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def record() -> dict[str, str]:
    tapes: dict[str, str] = {}

    lab = Lab()
    try:
        t = Tape(lab)
        t.say("A fresh sample passes every guard.")
        check(t)
        lab.set_break("orphan-doc", True)
        t.say("A runbook is added under docs/ and nobody adds it to the map.")
        check(t, "map-complete")
        lab.reset()
        lab.set_break("dead-link", True)
        t.say(
            "One row of the map links to a file that is not there. The checklist was only reachable through that row."
        )
        check(t, "map-links-live", "map-complete")
        tapes["map"] = t.render()

        lab.reset()
        t = Tape(lab)
        lab.set_break("adr-no-rejected", True)
        t.say("A decision record loses the section that says what was not chosen.")
        check(t, "adr-shape")
        lab.reset()
        lab.set_break("handoff-no-number", True)
        t.say("A handoff reports a suite state with nothing measured in it.")
        check(t, "handoff-shape")
        lab.reset()
        lab.set_break("skill-no-trigger", True)
        t.say("A skill is described by what it does, and not by when it applies.")
        check(t, "skill-shape")
        tapes["shape"] = t.render()

        lab.reset()
        t = Tape(lab)
        t.say("What a fresh session pays, measured on the sample. Token counts are characters divided by four.")
        t.run("docsguard budget", ["budget", "--root", str(lab.root)])
        lab.set_break("bloat", True)
        t.say("CLAUDE.md grows to 286 lines, one reasonable rule at a time.")
        check(t, "instruction-budget")
        tapes["budget"] = t.render()

        lab.reset()
        t = Tape(lab)
        lab.set_break("secret", True)
        t.say(
            "A cloud access key is pasted into the handoff. The finding names the file and the pattern, not the value."
        )
        check(t, "no-secrets")
        t.say("The same finding for a program: the JSON has a path, a line when there is one, and the message.")
        t.run(
            "docsguard check --rule no-secrets --json",
            ["check", "--root", str(lab.root), "--rule", "no-secrets", "--json"],
        )
        tapes["secrets"] = t.render()

        lab.reset()
        t = Tape(lab)
        t.say("Claude Code sends the hook a JSON payload on stdin. A command that discards work for good is denied.")
        hook(t, "git-guard", bash("git reset --hard HEAD~3"))
        t.say("The same command inside a wrapper is understood too.")
        hook(t, "git-guard", bash('bash -c "git reset --hard"'))
        t.say("An ordinary command: the hook prints nothing and the tool call goes ahead.")
        hook(t, "git-guard", bash("git status"))
        t.say("scope-guard: a write to a path that holds credentials is denied, and the reason says how to allow it.")
        hook(t, "scope-guard", {"tool_name": "Write", "tool_input": {"file_path": ".env"}}, with_cwd=True)
        tapes["hooks"] = t.render()
    finally:
        lab.close()
    return tapes


def render(tapes: dict[str, str]) -> str:
    return HEADER + "window.TRANSCRIPTS = " + json.dumps(tapes, indent=2, ensure_ascii=False) + ";\n"


def main() -> int:
    content = render(record())
    if "--check" in sys.argv:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != content:
            print(
                "site/transcripts.js does not match what the tool says: run scripts/record_transcripts.py",
                file=sys.stderr,
            )
            return 1
        print("transcripts match what the tool says")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
