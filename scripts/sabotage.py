#!/usr/bin/env python3
"""Mutation check by hand: break one behaviour at a time and require the matching tests to go red.

A guard that has never been seen failing is decoration. Each mutant below deletes or inverts one decision a
rule or hook makes; the named test file must then fail. The script restores every file byte-for-byte, proves
it did, and exits non-zero if any mutant survives.

    python scripts/sabotage.py            # all mutants
    python scripts/sabotage.py -k shell   # only those whose name contains "shell"
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "docsguard"


@dataclass(frozen=True)
class Mutant:
    name: str
    file: str  # relative to src/docsguard
    old: str
    new: str
    tests: str  # test module that must fail


MUTANTS: tuple[Mutant, ...] = (
    # --- docs map
    Mutant(
        "map-complete: orphans are not reported",
        "rules/docs_map.py",
        "if doc not in reachable",
        "if False",
        "tests/test_docs_map.py",
    ),
    Mutant(
        "map-complete: every document fans out, not only indexes",
        "rules/docs_map.py",
        'if target.rsplit("/", 1)[-1] in INDEX_NAMES:',
        "if True:",
        "tests/test_docs_map.py",
    ),
    Mutant(
        "map-links-live: dead links are not reported",
        "rules/docs_map.py",
        "if not repo.exists(target):",
        "if False:",
        "tests/test_docs_map.py",
    ),
    Mutant(
        "map-counts: a wrong count passes",
        "rules/docs_map.py",
        'if actual != int(attrs["expect"]):',
        "if False:",
        "tests/test_docs_map.py",
    ),
    Mutant(
        "claude-entrypoint: pointer to the map not required",
        "rules/docs_map.py",
        'if config.map_file not in repo.read("CLAUDE.md"):',
        "if False:",
        "tests/test_docs_map.py",
    ),
    Mutant(
        "repo: '..' in a link is not resolved", "repo.py", 'if part == "..":', "if False:", "tests/test_docs_map.py"
    ),
    Mutant(
        "repo: block-scalar front matter is not read",
        "repo.py",
        'if value in ("|", ">", "|-", ">-"):',
        "if value in ():",
        "tests/test_skills.py",
    ),
    # --- ADR
    Mutant(
        "adr: rejected alternatives not required",
        "rules/adr.py",
        "elif len(section_body(text, rejected)) < MIN_REJECTED_CHARS:",
        "elif False:",
        "tests/test_adr.py",
    ),
    Mutant(
        "adr: numbering gaps pass",
        "rules/adr.py",
        "for missing in sorted(expected - set(records)):",
        "for missing in []:",
        "tests/test_adr.py",
    ),
    Mutant(
        "adr: records missing from the index pass",
        "rules/adr.py",
        "if doc not in indexed",
        "if False",
        "tests/test_adr.py",
    ),
    Mutant(
        "adr: superseded-by a ghost passes",
        "rules/adr.py",
        "elif int(target.group(1)) not in numbers:",
        "elif False:",
        "tests/test_adr.py",
    ),
    Mutant("adr: duplicate numbers pass", "rules/adr.py", "if number in records:", "if False:", "tests/test_adr.py"),
    # --- handoff
    Mutant(
        "handoff: impossible dates pass",
        "rules/handoff.py",
        "datetime.date.fromisoformat(stamp.group(1))",
        "stamp.group(1)",
        "tests/test_handoff.py",
    ),
    Mutant(
        "handoff: a suite state without a number passes",
        "rules/handoff.py",
        'elif label == "suite state" and not re.search(r"\\d", body):',
        "elif False:",
        "tests/test_handoff.py",
    ),
    Mutant(
        "handoff: decisions need not cite an ADR",
        "rules/handoff.py",
        'if not cites_adr and not re.search(r"\\bnone\\b", body, re.IGNORECASE):',
        "if False:",
        "tests/test_handoff.py",
    ),
    Mutant(
        "handoff: missing sections pass", "rules/handoff.py", "if head is None:", "if False:", "tests/test_handoff.py"
    ),
    # --- budget
    Mutant(
        "budget: per-file cap not enforced",
        "rules/budget.py",
        "if f.lines > config.max_lines_per_file",
        "if False",
        "tests/test_budget.py",
    ),
    Mutant(
        "budget: total cap not enforced",
        "rules/budget.py",
        "if total > config.max_session_tokens:",
        "if False:",
        "tests/test_budget.py",
    ),
    Mutant(
        "budget: path-scoped rules are charged",
        "rules/budget.py",
        'if "paths" not in meta:',
        "if True:",
        "tests/test_budget.py",
    ),
    # --- skills
    Mutant(
        "skills: 'Use when' not required",
        "rules/skills.py",
        'elif "use when" not in description.lower():',
        "elif False:",
        "tests/test_skills.py",
    ),
    Mutant(
        "skills: name may differ from the directory",
        "rules/skills.py",
        'if meta.get("name") != name or not _NAME.match(name):',
        "if False:",
        "tests/test_skills.py",
    ),
    Mutant(
        "skills: oversize bodies pass",
        "rules/skills.py",
        "if tokens > config.max_skill_tokens:",
        "if False:",
        "tests/test_skills.py",
    ),
    Mutant(
        "skills: invalid-YAML descriptions pass",
        "rules/skills.py",
        're.search(r":\\s|\\s#", raw.group("value"))',
        "None",
        "tests/test_skills.py",
    ),
    # --- secrets
    Mutant(
        "secrets: placeholders are flagged",
        "rules/secrets.py",
        "if _PLACEHOLDER.search(candidate) or candidate.lower() in _DEV_DEFAULTS:",
        "if False:",
        "tests/test_secrets.py",
    ),
    Mutant(
        "secrets: dev defaults are flagged",
        "rules/secrets.py",
        " or candidate.lower() in _DEV_DEFAULTS",
        "",
        "tests/test_secrets.py",
    ),
    Mutant(
        "secrets: GitHub tokens are not recognised",
        "rules/secrets.py",
        "gh[pousr]_",
        "gx[pousr]_",
        "tests/test_secrets.py",
    ),
    Mutant(
        "secrets: private keys are not recognised",
        "rules/secrets.py",
        "-----BEGIN [A-Z ]*PRIVATE KEY-----",
        "-----BEGIN [A-Z ]*PRIVATE KEYS-----",
        "tests/test_secrets.py",
    ),
    # --- same-commit
    Mutant(
        "same-commit: added documents are not seen",
        "rules/staged.py",
        'if status == "A"',
        'if status == "Z"',
        "tests/test_staged.py",
    ),
    Mutant(
        "same-commit: a new ADR needs no index",
        "rules/staged.py",
        "if adr_index not in changes:",
        "if False:",
        "tests/test_staged.py",
    ),
    Mutant(
        "same-commit: a new document needs no map",
        "rules/staged.py",
        "elif config.map_file not in changes:",
        "elif False:",
        "tests/test_staged.py",
    ),
    # --- framework
    Mutant(
        "model: a guard that examined nothing passes",
        "model.py",
        "return self.skipped is None and self.examined == 0",
        "return False",
        "tests/test_cli.py",
    ),
    Mutant(
        "checks: a stale exemption is not reported", "checks.py", "if i not in used", "if False", "tests/test_config.py"
    ),
    Mutant(
        "checks: an exemption matches by rule alone",
        "checks.py",
        "e.rule == finding.rule and e.path == finding.path",
        "e.rule == finding.rule",
        "tests/test_config.py",
    ),
    Mutant(
        "config: dismissals need no reason",
        "config.py",
        "MIN_REASON_CHARS = 10",
        "MIN_REASON_CHARS = 0",
        "tests/test_config.py",
    ),
    Mutant("config: unknown keys are accepted", "config.py", "if unknown:", "if False:", "tests/test_config.py"),
    Mutant("cli: a failing check exits 0", "cli.py", "return 0 if report.ok else 1", "return 0", "tests/test_cli.py"),
    Mutant(
        "cli: a hook config error blocks the session",
        "cli.py",
        'return 2 if args.command != "hook" else 1',
        "return 2",
        "tests/test_cli.py",
    ),
    # --- shell analyser
    Mutant(
        "shell: wrappers are not stripped",
        "hooks/shell.py",
        "wrapper = WRAPPERS.get(posixpath.basename(head))",
        "wrapper = None",
        "tests/test_shell.py",
    ),
    Mutant(
        "shell: $(...) bodies are not scanned", "hooks/shell.py", "nested.append(inner)", "pass", "tests/test_shell.py"
    ),
    Mutant(
        "shell: backtick bodies are not scanned",
        "hooks/shell.py",
        "nested.append(command[i + 1 : end])",
        "pass",
        "tests/test_shell.py",
    ),
    Mutant(
        "shell: here-document bodies are parsed as commands",
        "hooks/shell.py",
        "i = _skip_heredocs(command, i, pending)",
        "i = i",
        "tests/test_shell.py",
    ),
    Mutant(
        "shell: bash -c is not followed",
        "hooks/shell.py",
        "return args[index + 1] if index + 1 < len(args) else None",
        "return None",
        "tests/test_shell.py",
    ),
    Mutant("shell: eval is not followed", "hooks/shell.py", 'if name == "eval":', "if False:", "tests/test_shell.py"),
    # --- git guard
    Mutant(
        "git-guard: reset --hard is allowed",
        "hooks/git_guard.py",
        'elif sub == "reset" and "--hard" in rest.long:',
        'elif sub == "reset" and False:',
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: +refspec force push is allowed",
        "hooks/git_guard.py",
        'any(p.startswith("+") for p in rest.positional)',
        "False",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: push --mirror is allowed",
        "hooks/git_guard.py",
        '"--mirror" in rest.long',
        "False",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: :branch remote deletion is allowed",
        "hooks/git_guard.py",
        'p.startswith(":") and len(p) > 1',
        "False",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: commit -n is allowed",
        "hooks/git_guard.py",
        '(sub == "commit" and "n" in rest.short)',
        "False",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: git is not recognised behind a path",
        "hooks/git_guard.py",
        'if posixpath.basename(tokens[0]) == "git":',
        'if tokens[0] == "git":',
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: clean --dry-run is denied",
        "hooks/git_guard.py",
        '"--dry-run" in rest.long',
        "False",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: restore --staged is denied",
        "hooks/git_guard.py",
        '("--staged" in rest.long or "S" in rest.short)',
        "False",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: core.hooksPath override is allowed",
        "hooks/git_guard.py",
        'if setting.lower().startswith("core.hookspath"):',
        "if False:",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: stash drop is allowed",
        "hooks/git_guard.py",
        'elif sub == "stash" and rest.positional[:1] in (["drop"], ["clear"]):',
        "elif False:",
        "tests/test_git_guard.py",
    ),
    Mutant(
        "git-guard: option clusters swallow message text",
        "hooks/git_guard.py",
        "if letter in _VALUE_LETTERS:",
        "if False:",
        "tests/test_git_guard.py",
    ),
    # --- scope guard
    Mutant(
        "scope-guard: symlinks are not resolved",
        "hooks/scope_guard.py",
        "resolved = Path(os.path.realpath(absolute))",
        "resolved = absolute",
        "tests/test_scope_guard.py",
    ),
    Mutant(
        "scope-guard: an authorization needs no reason",
        "hooks/scope_guard.py",
        "(?P<needle>\\S+)\\s+--\\s+(?P<reason>\\S.*)$",
        "(?P<needle>\\S+)(?:\\s+--\\s+(?P<reason>\\S.*))?$",
        "tests/test_scope_guard.py",
    ),
    Mutant(
        "scope-guard: .env.example is protected",
        "hooks/scope_guard.py",
        "if posixpath.basename(relative) in ALLOWED_EXCEPTIONS:",
        "if False:",
        "tests/test_scope_guard.py",
    ),
    Mutant(
        "scope-guard: shell writes are not inspected",
        "hooks/scope_guard.py",
        'elif tool == "Bash" and isinstance(data.get("command"), str):',
        "elif False:",
        "tests/test_scope_guard.py",
    ),
    Mutant(
        "scope-guard: authorizations are ignored",
        "hooks/scope_guard.py",
        "if any(needle in relative or needle in absolute for needle in authorizations.needles):",
        "if False:",
        "tests/test_scope_guard.py",
    ),
    Mutant(
        "scope-guard: redirections are not seen",
        "hooks/scope_guard.py",
        "if match:\n                target =",
        "if False:\n                target =",
        "tests/test_scope_guard.py",
    ),
)


def tree_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(SRC.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(SRC).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def run_tests(tests: str) -> tuple[int, str]:
    """``(pytest exit code, one line of evidence)``.

    Only exit code 1 means "a test failed". Codes 2-5 (collection error, internal error, usage, no tests) are
    what a mutant that merely breaks the syntax produces, and they prove nothing about the tests.
    """
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-x", "-rf", "--no-header", "-p", "no:cacheprovider", tests],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=300,
        check=False,
    )
    lines = done.stdout.splitlines()
    failed = next((ln for ln in lines if ln.startswith("FAILED ")), "")
    if failed:
        evidence = failed.removeprefix("FAILED ").split(" - ")[0].split("::", 1)[-1]
    else:
        evidence = next((ln for ln in reversed(lines) if " passed" in ln or "error" in ln), "").strip()
    return done.returncode, evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-k", dest="keyword", default="", help="only mutants whose name contains this text")
    args = parser.parse_args()

    # The unmutated suite must be green first, or "killed" would mean nothing.
    for tests in sorted({m.tests for m in MUTANTS}):
        code, summary = run_tests(tests)
        if code != 0:
            print(f"baseline is not green for {tests} (exit {code}): {summary}")
            return 2

    before = tree_hash()
    survivors: list[str] = []
    selected = [m for m in MUTANTS if args.keyword in m.name]
    print(f"{len(selected)} mutants; each must turn its test file red\n")
    for mutant in selected:
        path = SRC / mutant.file
        original = path.read_text(encoding="utf-8")
        if original.count(mutant.old) != 1:
            print(f"  [setup error] {mutant.name}: pattern occurs {original.count(mutant.old)} times in {mutant.file}")
            survivors.append(mutant.name)
            continue
        try:
            path.write_text(original.replace(mutant.old, mutant.new), encoding="utf-8")
            code, summary = run_tests(mutant.tests)
        finally:
            path.write_text(original, encoding="utf-8")
        if code == 1:
            print(f"  killed    {mutant.name}\n              by {summary}")
        elif code == 0:
            print(f"  SURVIVED  {mutant.name}   ({summary})")
            survivors.append(mutant.name)
        else:
            print(f"  INVALID   {mutant.name}: pytest exit {code}, the mutant did not even run ({summary})")
            survivors.append(mutant.name)

    if tree_hash() != before:
        print("\nSOURCE TREE CHANGED: restore it manually")
        return 3
    print(f"\nsource tree restored byte-for-byte; survivors: {len(survivors)}")
    return 1 if survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
