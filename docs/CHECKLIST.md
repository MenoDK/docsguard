# Master checklist

*What* and *when*. The *how* lives in the code and tests, the *why* in the ADRs.

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Nine documentation guards plus `same-commit` | done | `src/docsguard/rules/`, `tests/` |
| 2 | Two PreToolUse hooks (git, scope) with a shell analyser | done | `src/docsguard/hooks/`, [ADR 0003](adr/0003-hooks-denylist-and-fail-open.md) |
| 3 | Every behaviour pinned by a mutant | done | `scripts/sabotage.py`, 0 survivors on the last run |
| 4 | `docsguard init` template that passes its own guards | done | `tests/test_template.py` |
| 5 | The repository passes its own guards | done | `tests/test_dogfood.py` |
| 6 | Container image and compose service | done | `Dockerfile`, `docker-compose.yml` |
| 7 | CI: lint, types, tests, dogfood, mutation, package, image, browser, secrets | written | `.github/workflows/ci.yml`; see the handoff for the last run |
| 8 | Reusable GitHub Action | written | `action.yml`; not yet run from another repository |
| 9 | Nested YAML front matter | dropped | out of scope on purpose: [ADR 0002](adr/0002-standard-library-only.md) |
| 10 | Exact token counts | dropped | [ADR 0004](adr/0004-token-estimate-by-characters.md) |
| 11 | Playground: the real guards on a sample project you can break | done | `playground/`, `tests/test_playground_*.py`, [ADR 0007](adr/0007-the-playground-runs-the-real-guards-and-executes-nothing.md) |
| 12 | Landing page, lab page and the tour recorded from the real tool | done | `site/`, `scripts/record_transcripts.py` (`--check` in CI) |
| 13 | Landing and lab in 14 languages | done | `site/i18n/`; machine translation, a native review is still owed |
| 14 | Black-box smoke test over the lab's HTTP API | done | `scripts/smoke.sh` (38 checks) |
| 15 | Browser tests with an accessibility scan | done | `e2e/` (57 tests; Playwright and axe) |
| 16 | Authentication for the lab | dropped | local tool: loopback, off unless asked, refused in production ([ADR 0007](adr/0007-the-playground-runs-the-real-guards-and-executes-nothing.md)) |
| 17 | A guard for links from documents to code symbols | todo | a document that names a function that was renamed |

Status is one of `todo`, `doing`, `done`, `written` (exists, not yet exercised where it will run), `dropped`.
