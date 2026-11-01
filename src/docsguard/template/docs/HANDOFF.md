# Handoff

Updated: {{date}}

Rewrite this file at the end of every session. A fresh session must be able to resume from disk alone.

## 1. What is live

Nothing yet: the repository has just been initialised from the template.

## 2. Where we stopped

Template installed. Next step: fill in the commands in `AGENTS.md` and the description in `CLAUDE.md`.

## 3. What the owner does now

Install the guard (`pipx install git+https://github.com/MenoDK/docsguard`) so the hooks in `.claude/settings.json` can run; until then they do nothing.

## 4. Deadlines

None.

## 5. What NOT to do

- Do not paste long instructions into `CLAUDE.md`; link a document through the map instead.
- Do not mark an item done without the output of the check that proves it.

## 6. Decisions

- Decisions are recorded as ADRs: [ADR 0001](adr/0001-record-architecture-decisions.md).

## 7. Learned, not in the code

Nothing yet.

## 8. Suite state

`docsguard check`: 9 rules run, 0 findings, measured on {{date}}. Project tests: not configured yet.
