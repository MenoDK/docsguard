# 0005. A guard that examined nothing fails

Status: Accepted

## Context

The most common way for a check to be worthless is to pass because it looked at nothing: a glob that matches no file,
a directory that was renamed, a parser that returns an empty list. The suite stays green and the number reads 0 failures,
so nobody looks. Every rule here has a path to that outcome.

## Decision

Every rule reports `examined`, the count of items it actually looked at. `check` fails any rule whose `examined` is 0
unless the rule returned an explicit `skipped=<reason>`, which is printed. The template and this repository are required
to give every non-skipped rule real input (`test_every_guard_examined_something_on_the_template`, `test_dogfood.py`).

## Rejected alternatives

- **Treat zero items as a pass.** The classic silent failure.
- **Warn but exit 0.** A warning nobody reads is a pass.
- **A global "fail if anything was skipped".** Some rules legitimately do not apply (no ADR directory yet); forcing noise
  there teaches people to ignore it. Explicit, printed skips keep the signal.

## Consequences

A repository that has not adopted a part of the system sees `skipped: no docs/adr directory`, which is accurate, and a
repository that broke it sees a failure.
