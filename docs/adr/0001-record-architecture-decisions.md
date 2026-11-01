# 0001. Record architecture decisions

Status: Accepted

## Context

The decisions that shaped this tool (what a hook does with input it cannot parse, why tokens are estimated, why
there are no dependencies) are not visible in the code, which only shows what was done. A reader, or a fresh AI
session with no memory, would have to reverse-engineer the reasons, and would be tempted to "fix" a deliberate choice.

## Decision

Every decision that a newcomer would otherwise have to reverse-engineer gets a record in `docs/adr/`, written before
the implementation, with the alternatives that lost and why. Accepted records are not edited: a change of mind is a
new record that supersedes the old one. `docsguard` itself checks the shape and the index (`adr-shape`).

## Rejected alternatives

- **Commit messages only.** They say what changed; they are not findable by topic and carry no rejected alternatives.
- **A wiki outside the repository.** It drifts from the code and cannot fail a build.
- **No records.** Cheapest today, paid for by every later reader.

## Consequences

A little writing before each significant change. In return the *why* survives, and the tool can verify it is complete.
