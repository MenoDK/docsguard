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
| 7 | CI: lint, types, tests, dogfood, mutation, package, image, secrets | written | `.github/workflows/ci.yml`; not yet run on GitHub |
| 8 | Reusable GitHub Action | written | `action.yml`; not yet run on GitHub |
| 9 | Nested YAML front matter | dropped | out of scope on purpose: [ADR 0002](adr/0002-standard-library-only.md) |
| 10 | Exact token counts | dropped | [ADR 0004](adr/0004-token-estimate-by-characters.md) |

Status is one of `todo`, `doing`, `done`, `written` (exists, not yet exercised where it will run), `dropped`.
