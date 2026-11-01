# 0002. Standard library only at run time

Status: Accepted

## Context

The guard runs in three places that share one property, *it must work without setup*: as a Claude Code hook on every
tool call, in the CI of arbitrary repositories, and on a contributor's laptop. A hook that needs `pip install` first
is a hook that is silently not running on the machine where it was forgotten. Python 3.11 ships `tomllib`, which was
the one thing that used to need a package.

## Decision

`dependencies = []`. Development tools (pytest, ruff, mypy) are dev-only. Configuration is validated by hand in
`config.py`, front matter by a small flat-key reader in `repo.py`, the CLI is `argparse`.

## Rejected alternatives

- **PyYAML for front matter.** Needs an install, and the rules only read flat keys (`name`, `description`, `paths`).
  Cost accepted: nested YAML is ignored rather than guessed at, and block scalars are the only extension supported.
- **pydantic for configuration.** Strict and pleasant, but a dependency for roughly sixty lines of explicit validation.
- **click or rich for the command line.** Nothing here needs more than subcommands and flags.
- **Shell scripts.** No unit tests, no types, and quoting bugs in a tool whose job is to parse shell.
- **A single-file binary (zipapp, PyInstaller).** Solves distribution, not the real problem; revisit if adoption needs it.

## Consequences

Slightly more code than with libraries, all of it under mypy `--strict` and covered by mutants. The tool installs and
runs anywhere Python 3.11 does.
