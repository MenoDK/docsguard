# Agent contract

Tool-neutral: what any engineer or coding agent needs to work here without asking.

## Commands

| Task | Command |
| --- | --- |
| Install (dev) | `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'` |
| Everything CI runs, minus Docker | `make check` |
| Tests only | `.venv/bin/pytest` |
| Lint and format check | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` |
| Types (strict) | `.venv/bin/mypy` |
| Mutation proof | `.venv/bin/python scripts/sabotage.py` |
| This repo's own guards | `.venv/bin/docsguard check` |
| Session cost, measured | `.venv/bin/docsguard budget` |
| The lab and the landing page (needs Docker) | `make playground`, then http://localhost:8200 |
| Black-box checks of the running lab | `make smoke` |
| Browser tests (Playwright, axe, 14 languages) | `make e2e` |
| Re-record the tour on the landing page | `make transcripts` (CI runs it with `--check`) |

## Definition of done

1. The test that covers the change exists and fails without it.
2. `make check` passes and you can quote its output.
3. A new or changed guard has a mutant in `scripts/sabotage.py`, and `sabotage.py` reports 0 survivors.
4. `docs/HANDOFF.md` carries the numbers that were printed, not the ones that were expected.

## Boundaries

- Runtime dependencies stay at zero (`docs/adr/0002`). Dev tools are fine.
- No literal that looks like a credential, even in a test; assemble it at run time.
- Do not edit `src/docsguard/template/` without running `tests/test_template.py`: it is the shipped product.
- The playground never executes what it is asked about, and never runs with the lab on in production
  (`docs/adr/0007`). A change to `playground/` gets a test and, if it is a decision, a mutant in `scripts/sabotage.py`.
- `site/kit.css`, `site/kit.js` and `site/i18n/ui.js` are a shared kit: change the text of this project in
  `site/content.js`, `site/lab.js` and `site/i18n/<code>.js`, not in the kit.
- Anything outside the task goes into `docs/CHECKLIST.md`, not into this change.

## Reporting

Say what happened, not what was expected. A failed test, a skipped check or an unverified claim goes in the report as it is.
