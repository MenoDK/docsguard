# docsguard

Executable guards for project-oriented documentation and Claude Code workflows: it checks that the docs map is
complete, ADRs and handoffs have their shape, session-start instructions fit a budget, and it ships the two
PreToolUse hooks (destructive git, protected paths). Python 3.11+, standard library only.

## Start here

- Map of every document: [docs/00-READ-FIRST.md](docs/00-READ-FIRST.md). Open a document only when the map says to.
- Resuming work: `docs/HANDOFF.md` first; rewrite it before you stop.
- Commands and definition of done: @AGENTS.md

## Layout

- `src/docsguard/rules/`: one module per family of guards; each returns a `RuleResult` (what it examined, what it found).
- `src/docsguard/hooks/`: `shell.py` (command analyser), `git_guard.py`, `scope_guard.py`, `protocol.py` (wire format).
- `src/docsguard/template/`: what `docsguard init` installs. `dot-claude/` becomes `.claude/` on install.
- `tests/`: one file per module. `scripts/sabotage.py`: mutation proof for every guard.

## Rules that apply to every task

1. **Every behaviour a guard has is pinned by a mutant.** Add a rule, add its test, add its mutant to
   `scripts/sabotage.py`, and see the mutant die. A guard never seen failing is decoration.
2. **A guard that examines nothing fails.** Return `examined` honestly; use `skipped=` with a reason, never a silent pass.
3. **The template must pass its own guards.** `test_template.py` initialises it and runs `check`.
4. **Hooks fail open on input they cannot parse**, and say why in `docs/adr/0003`. Never make one block on its own bug.
5. **No secret-shaped literal in source or tests.** Build fixtures at run time (see `tests/test_secrets.py`).
6. **One home per fact.** Link to the ADR; do not restate it here.

Advice versus enforcement: this file is advice. `.claude/settings.json` wires the hooks this project ships, so they
guard the project that builds them.
