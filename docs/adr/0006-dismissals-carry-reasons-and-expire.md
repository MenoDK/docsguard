# 0006. Every dismissal carries a written reason, and stale ones are reported

Status: Accepted

## Context

A guard with an escape hatch needs the hatch to be visible, justified and temporary, or it becomes the way the guard
is turned off one exception at a time. Inline "ignore" comments are invisible in review; a global off-switch is too blunt.

## Decision

Exemptions live in `docsguard.toml` as `[[exempt]]` tables with `rule`, `path` and a `reason` of at least ten characters;
without one, loading the configuration fails. An exemption that no longer matches any finding is itself reported
(`exemptions`), so dismissals cannot outlive the thing they dismissed. The same holds for protected paths (`reason`
required) and for write authorizations (`path:<needle> -- <reason>`).

## Rejected alternatives

- **Inline ignore comments.** Scattered, invisible in review, never removed.
- **An allowlist file without reasons.** Becomes a list of things nobody remembers the cause of.
- **A global `--no-verify` style bypass.** Disables every guard to silence one.

## Consequences

Mild friction when adding an exemption, which is the point. The reason is part of the diff and can be questioned in review.
