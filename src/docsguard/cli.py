"""Command line: ``check``, ``budget``, ``init``, ``rules`` and the two ``hook`` entry points."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, budget_report, scaffold
from .checks import RULES, STAGED_RULE, render, run_checks
from .config import ConfigError, load
from .hooks import git_guard, scope_guard
from .repo import Repo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docsguard", description=__doc__)
    parser.add_argument("--version", action="version", version=f"docsguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="run the guards; exit 1 when any fails")
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--staged", action="store_true", help="also check the staged change (same-commit rule)")
    check.add_argument("--rule", action="append", dest="rules", help="run only this rule (repeatable)")
    check.add_argument("--json", action="store_true", help="machine-readable output")

    budget = sub.add_parser("budget", help="what a fresh session pays, against reading every doc")
    budget.add_argument("--root", type=Path, default=Path.cwd())
    budget.add_argument("--json", action="store_true")

    init = sub.add_parser("init", help="copy the docs + Claude workflow template into a repository")
    init.add_argument("target", type=Path)
    init.add_argument("--name", required=True, help="project name used in the templates")
    init.add_argument("--force", action="store_true", help="overwrite files that already exist")

    sub.add_parser("rules", help="list the guards and what each one means")

    hook = sub.add_parser("hook", help="PreToolUse hook entry points (payload on stdin)")
    hook.add_argument("which", choices=["git-guard", "scope-guard"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _dispatch(args)
    except ConfigError as error:
        print(f"docsguard: {error}", file=sys.stderr)
        return 2 if args.command != "hook" else 1  # a hook must not block the session over its own config


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "hook":
        return (
            git_guard.run(sys.stdin, sys.stdout)
            if args.which == "git-guard"
            else scope_guard.run(sys.stdin, sys.stdout)
        )

    if args.command == "rules":
        for name, (_, meaning) in {**RULES, STAGED_RULE[0]: STAGED_RULE[1]}.items():
            print(f"{name:<20} {meaning}")
        return 0

    if args.command == "init":
        created, skipped = scaffold.init(args.target, args.name, force=args.force)
        for path in created:
            print(f"created  {path}")
        for path in skipped:
            print(f"kept     {path} (exists; --force to overwrite)")
        print(f"\n{len(created)} created, {len(skipped)} kept. Next: docsguard check --root {args.target}")
        return 0

    repo = Repo(args.root)
    config = load(repo.root)
    if args.command == "budget":
        data = budget_report.build(repo, config)
        print(json.dumps(data, indent=2) if args.json else budget_report.render(data))
        return 0

    try:
        report = run_checks(repo, config, staged=args.staged, only=args.rules)
    except KeyError as error:
        print(f"docsguard: {error.args[0]}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "ok": report.ok,
                    "results": [
                        {
                            "rule": r.rule,
                            "examined": r.examined,
                            "skipped": r.skipped,
                            "vacuous": r.vacuous,
                            "findings": [{"path": f.path, "line": f.line, "message": f.message} for f in r.findings],
                        }
                        for r in report.results
                    ],
                },
                indent=2,
            )
        )
    else:
        print(render(report, str(repo.root)))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
