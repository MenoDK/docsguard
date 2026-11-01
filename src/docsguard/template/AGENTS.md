# Agent contract

Tool-neutral. Anything an engineer or any coding agent needs to work here without asking.

## Commands

| Task | Command |
| --- | --- |
| Install | `<fill in>` |
| Test | `<fill in>` |
| Lint and types | `<fill in>` |
| Documentation guards | `docsguard check` |

## Definition of done

A change is done when, in this order:

1. the tests that cover it exist, and fail without the change;
2. the full suite and the documentation guards pass, and you can quote their output;
3. an ADR exists for any decision a newcomer would otherwise have to reverse-engineer;
4. `docs/HANDOFF.md` says where things stand, with measured numbers rather than expectations.

## Boundaries

- Do not edit generated files, lockfiles by hand, or anything listed under `[[scope.protected]]` in `docsguard.toml`.
- Do not widen scope. If you find an unrelated problem, write it in `docs/CHECKLIST.md` instead of fixing it now.
- Ask before: deleting data, changing a public interface, adding a dependency.

## Reporting

Say what happened, not what was expected. A failing test, a skipped check or an unverified claim goes in the report
as it is. Retractions are written down, not quietly dropped.
