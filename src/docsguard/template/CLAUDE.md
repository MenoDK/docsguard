# {{project}}

<!-- One paragraph: what this project is, for whom, and the one constraint that shapes everything. -->

## Start here

- Map of every document: [docs/00-READ-FIRST.md](docs/00-READ-FIRST.md). Open a document only when the map says to.
- Resuming work: read `docs/HANDOFF.md` first. Before you stop, rewrite it.
- Cross-tool contract (commands, definition of done): @AGENTS.md

## Rules that apply to every task

1. **Precedence when sources disagree:** code, then ADRs, then measured patterns, then this file. The code wins
   because it is what runs; fix the document, not the code, unless the code is the bug.
2. **Decide on paper first.** A non-trivial decision gets an ADR with the rejected alternatives *before* the code.
3. **Never say "done" without evidence.** Run the checks in AGENTS.md and report what they printed.
4. **One home per fact.** If a fact is in an ADR, link to it; do not copy it here.
5. **Docs are code.** A new document is added to the map in the same commit; `docsguard check` must pass.
6. **Secrets never enter a document, a prompt or a commit.** Fingerprint with `sha256 | cut -c1-12` if you must refer to one.

## What is enforced, and what is only advice

This file is advice. Hooks in `.claude/settings.json` are blocking: destructive git and writes to protected paths
are refused. If a hook blocks you, read its reason; do not look for a way around it.

<!-- Keep this file under ~60 lines. Detail belongs in docs/, opened on demand through the map. -->
