# Handoff

Updated: 2026-11-01

Rewritten at the end of every session. A fresh session must be able to resume from disk alone.

## 1. What is live

Nothing is deployed: this is a library and CLI. The package builds as `docsguard 0.1.0`; the container image and compose
service are defined but have not been published anywhere.

## 2. Where we stopped

The tool, tests, mutation script, template, own documentation and delivery files (README, Dockerfile, compose, CI,
action) are written. Next: run the container and package checks, a final secret scan, then `git init` and the first commit.

## 3. What the owner does now

Push the repository to GitHub when ready. Until it runs there, the CI workflow and `action.yml` are written but unexercised.

## 4. Deadlines

None.

## 5. What NOT to do

- Do not add a runtime dependency: [ADR 0002](adr/0002-standard-library-only.md).
- Do not make a hook block on input it cannot parse: [ADR 0003](adr/0003-hooks-denylist-and-fail-open.md).
- Do not accept a mutant that merely breaks the syntax as "killed": `sabotage.py` requires pytest exit code 1.
- Do not put a literal that looks like a credential in a test; assemble it at run time.

## 6. Decisions

- Record keeping, standard library only, hook policy, token estimate, vacuity, dismissals:
  [ADR 0001](adr/0001-record-architecture-decisions.md) to [ADR 0006](adr/0006-dismissals-carry-reasons-and-expire.md).

## 7. Learned, not in the code

- A test whose condition is always true (`or "." in reason`) passed on the first run and tested nothing. A guard's own
  tests need the same sabotage proof as the guards.
- `pkill -f jest` matches the shell that launched it. Use a pid, not a pattern.
- Counting a syntax-breaking mutant as "killed" inflated the first mutation report; only an assertion failure counts.

## 8. Suite state

Measured on 2026-11-01: 337 tests passing, 60 mutants killed with 0 survivors, `ruff` and `mypy --strict` clean,
`docsguard check` passing on this repository with 9 rules examined.
