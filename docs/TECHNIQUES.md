# Techniques

The working method behind this repository, one technique per section: what it is, what it prevents, and where it is
enforced in code. The ideas are old (progressive disclosure, architecture fitness functions, decision records); what is
added is that each one is **checked by a program** instead of left to discipline.

| # | Technique | Prevents | Enforced by |
| --- | --- | --- | --- |
| 1 | A map, not content | paying to load documents nobody needed | `map-complete`, `map-links-live`, `map-counts`, `docsguard budget` |
| 2 | Four living documents | losing the thread between sessions | `adr-shape`, `handoff-shape` |
| 3 | Decisions on paper first, with the losers | re-deciding, and "fixing" what was deliberate | `adr-shape` |
| 4 | A bounded session-start budget | instructions that cost every turn and are followed less | `instruction-budget` |
| 5 | Precedence, written down | two sources disagreeing with no way to settle it | `.claude/rules/precedence.md` |
| 6 | Guards, proven by sabotage | a class of error coming back; a green check that checks nothing | `scripts/sabotage.py`, ADR 0005 |
| 7 | Advice versus enforcement (hooks) | "never do X" being forgotten at 2 a.m. | `hooks/git_guard.py`, `hooks/scope_guard.py` |
| 8 | Compressed subagent contracts | a research task flooding the main context | `template/dot-claude/agents/` |
| 9 | Skills that can be found and survive compaction | skills never loaded, or truncated mid-instruction | `skill-shape` |
| 10 | The bridge protocol | two agents contradicting each other through memory | `template/docs/bridge/PROTOCOL.md` |
| 11 | Same-commit discipline | the index going stale the day a document is added | `same-commit` (`check --staged`) |
| 12 | No secrets or infrastructure names in documents | credentials travelling in prompts and exports | `no-secrets` |
| 13 | A knowledge tree | studying everything when the task needs one branch | `template/docs/knowledge-tree/` |

## 1. A map, not content

`docs/00-READ-FIRST.md` is a table of "open when you…" rows pointing at documents. It contains no content of its own, so
a fresh session reads one small file and then opens only what the task needs. This is progressive disclosure applied to
context: the cost of a session is the map plus the branches actually opened, not the whole documentation tree.

Three rules keep it honest. A new document is added to the map in the same commit that creates it (a stale index is a
defect). Counts the map states ("6 ADRs") are written as a marker and compared with the disk. `CLAUDE.md` mirrors the map
and never the other way round. `docsguard budget` prints the measured cost of a session start against reading everything.

## 2. Four living documents

| Document | Answers | Rule |
| --- | --- | --- |
| `CHECKLIST.md` | what, and when | a `done` row names the evidence; a dropped row is marked, never deleted |
| task notes | how | carries `path:line` evidence |
| `adr/` | why | written before the code, with the rejected alternatives |
| `HANDOFF.md` | where we stopped | rewritten, never appended to |

The test of the set: *can a fresh session resume from disk alone?* The handoff has eight required sections, among them
**what NOT to do** (the traps already fallen into), **decisions** (each linked to its ADR) and **suite state**, which must
contain a number: report what happened, not what was expected.

## 3. Decisions on paper first

An ADR is written before the implementation, so it is a decision and not a justification. It must say what lost and why;
an ADR with no rejected alternative is a changelog entry. Measured facts carry their date. Accepted records are not
edited: a change of mind supersedes, and the old record says by which.

## 4. A bounded session-start budget

A session pays, on every turn, for `CLAUDE.md`, everything it imports with `@path`, and every unscoped file under
`.claude/rules/`. That set is capped per file (default 200 lines: long instructions are followed less reliably) and in
total (default ~6,000 estimated tokens). Detail lives in on-demand documents. Path-scoped rules (`paths:` front matter)
load only when relevant and are not charged.

## 5. Precedence, written down

When sources disagree: **code, then ADRs, then measured patterns, then `CLAUDE.md`, then `AGENTS.md`.** The code wins
because it is what runs; the fix is to the document unless the code is the bug. The file is deliberately unscoped so it
is loaded in every session.

## 6. Guards, proven by sabotage

A guard is a test that fails when a *class* of error reappears. Five habits make guards trustworthy:

1. **Derive, do not list.** Compute the set under test from disk or code so a new member is covered automatically.
2. **Accuse at the defect's granularity.** A finding names the file and line, not "something is wrong".
3. **Every dismissal carries a written reason**, and a dismissal that stops matching is reported (ADR 0006).
4. **Prove it can fail.** `scripts/sabotage.py` deletes or inverts one decision at a time and requires the
   matching test to fail with an *assertion*, not a crash: a mutant that only breaks the syntax proves nothing.
5. **Prove it sees something.** A guard that examined zero items fails (ADR 0005).

## 7. Advice versus enforcement

`CLAUDE.md` is a request. A hook is a rule. `git-guard` refuses the commands that destroy unrecoverable work, names the
safer alternative, and understands disguises (`sudo`, `env`, `bash -c`, `&&`, `$(…)`) while ignoring commands that merely
mention them (a heredoc commit message). `scope-guard` refuses writes to protected paths, never blocks reads, and is
overridden only by a committed line with a reason. Both fail open on input they cannot parse (ADR 0003) and neither is a
security boundary.

## 8. Compressed subagent contracts

Everything a subagent returns is injected into the main context. A subagent told to "report your findings" returns an
essay. The agents in the template carry an **output contract**: the investigator answers in `ANSWER / EVIDENCE / UNKNOWN`
at most fifteen lines; the reviewer in `VERDICT / BLOCKERS / NITS / CHECKED`, a blocker needing a failing scenario.
The effect is bounded by construction rather than by hope. No savings figure is claimed here; measure it on your own tasks.

## 9. Skills that can be found and survive compaction

A skill is loaded from its `description`, so the description must say *when* ("Use when…"), and as valid YAML (an unquoted
`: ` breaks it). Skill bodies are truncated after a conversation is compacted (per the Claude Code documentation at the time
of writing), so the instruction that matters goes first and the body stays under a token cap.

## 10. The bridge protocol

When two agents or tools coordinate, they do it through files with one author each, rewritten rather than accumulated,
opening with a state block, and never carrying a secret (only a `sha256 | cut -c1-12` fingerprint) or personal data. A
decision counts only once it is in an ADR or the checklist. See `template/docs/bridge/PROTOCOL.md`.

## 11. Same-commit discipline

`docsguard check --staged` fails the commit that adds a document without touching the map, or an ADR without the ADR
index: the moment an index goes stale, and the cheapest moment to prevent it. Wire it as a pre-commit hook or a CI step.

## 12. No secrets or infrastructure names in documents

Documentation is pasted into prompts, exported and committed. `no-secrets` scans `CLAUDE.md`, `AGENTS.md`, `docs/` and
`.claude/` for key blocks, tokens, URL credentials and cloud identifiers (managed-database hosts, account ids in ARNs),
and reports the pattern and the line, never the match.

## 13. A knowledge tree

A way to study something unfamiliar without loading all of it: a root question stated with real numbers, branches opened
on demand, and a maturity level that moves only on evidence (a measurement, a passing test), never on time spent.
YAGNI applies to study: no branch is opened for a thing no task needs yet.
