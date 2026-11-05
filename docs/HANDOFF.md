# Handoff

Updated: 2026-11-05

Rewritten at the end of every session. A fresh session must be able to resume from disk alone.

## 1. What is live

Nothing is deployed: this is a library, a CLI and a local lab. The package builds as `docsguard 0.1.0`. The lab runs from
`make playground` on http://localhost:8200 (loopback only); the image is built locally and published nowhere.

## 2. Where we stopped

The tool, the playground (`playground/`), the landing page and lab page in 14 languages (`site/`), the black-box smoke
script, the browser tests (`e2e/`), the mutation script (now covering the lab's doors) and the delivery files (README,
Dockerfile with a `playground` stage, compose, CI, action) are written and were run locally. Next: the first push and the
first run of the CI workflow on GitHub.

## 3. What the owner does now

Push the repository to GitHub when ready, watch the first CI run, and ask a native speaker to read the Hindi, Bengali,
Urdu and Arabic text of the site: it is machine translation. Until the workflow has run there, it is written but unexercised.

## 4. Deadlines

None.

## 5. What NOT to do

- Do not add a runtime dependency: [ADR 0002](adr/0002-standard-library-only.md).
- Do not make a hook block on input it cannot parse: [ADR 0003](adr/0003-hooks-denylist-and-fail-open.md).
- Do not make the lab execute, evaluate or shell out with anything a visitor typed, and do not let it start with the lab on
  in production: [ADR 0007](adr/0007-the-playground-runs-the-real-guards-and-executes-nothing.md).
- Do not answer a request before its body has been read, or close the connection when it has not.
- Do not accept a mutant that merely breaks the syntax as "killed": `sabotage.py` requires pytest exit code 1.
- Do not put a literal that looks like a credential in a test; assemble it at run time.
- Do not edit `site/kit.css`, `site/kit.js` or `site/i18n/ui.js` here: they are a shared kit, synced from one place.

## 6. Decisions

- Record keeping, standard library only, hook policy, token estimate, vacuity, dismissals, the playground:
  [ADR 0001](adr/0001-record-architecture-decisions.md) to [ADR 0007](adr/0007-the-playground-runs-the-real-guards-and-executes-nothing.md).

## 7. Learned, not in the code

- A test whose condition is always true (`or "." in reason`) passed on the first run and tested nothing. A guard's own
  tests need the same sabotage proof as the guards.
- `pkill -f jest` matches the shell that launched it. Use a pid, not a pattern.
- Counting a syntax-breaking mutant as "killed" inflated the first mutation report; only an assertion failure counts.
- The one real bug of the playground appeared only when a browser reused a connection: a `POST` refused with 403 left its
  body unread, and the next request on that connection was parsed from the middle of it (a 501). Every unit test opened a
  new connection per request and passed. Test over a real socket, with two requests on one connection.
- Docker creates a missing bind-mount source as root: `mkdir -p docs/img` before `make e2e`.
- The mutation script rewrites source files in place: do not build the image while it runs, or the image may carry a mutant.

## 8. Suite state

Measured on 2026-11-05: 451 Python tests passing, 38 smoke checks passing against the running lab, 57 browser tests
passing (Playwright and axe, 14 languages), 86 mutants killed with 0 survivors, `ruff` and `mypy --strict` clean,
`hadolint` and `actionlint` clean, `docsguard check` passing on this repository with 9 rules examined. Not run yet:
the GitHub Actions workflow, and `action.yml` from another repository.
