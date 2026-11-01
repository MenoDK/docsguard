# 0003. Hooks are a denylist, they fail open, and they are not a security boundary

Status: Accepted

## Context

Two hooks guard a coding session: one refuses git commands that destroy unrecoverable work, one refuses writes to
protected paths. They sit on the hot path of every tool call, so two kinds of error are expensive. A **false
positive** (blocking a harmless command) gets the hook removed by the first person it interrupts. A **parse failure
that blocks** turns a bug in the hook into a stopped session. Meanwhile commands are routinely disguised without
malice: `sudo`, `env`, `bash -c '…'`, `a && b`, `$(…)`, and commit messages that merely *mention* `git reset --hard`.

## Decision

1. **Denylist by class of damage**, each denial naming the safer alternative (`--force-with-lease`, `git stash`,
   `git clean -n`), so the refusal is also the instruction.
2. Commands are analysed by a small shell scanner (`hooks/shell.py`) that understands quoting, separators, here-documents,
   substitutions and wrappers, so the *real* command is judged rather than the raw string.
3. **Fail open:** input the hook cannot parse is allowed. A broken configuration is reported on stderr with exit code 1,
   which Claude Code shows without blocking; only exit code 2 blocks, and the hooks never return it.
4. **Reads are never blocked.** Writes to a protected path are allowed only by a committed line
   `path:<substring> -- <reason>`; a line without a reason is ignored.
5. The README states plainly that this prevents accidents and is **not** a security boundary.

## Rejected alternatives

- **Allowlist of git commands.** Blocks every new harmless command until someone edits the list, which is exactly when
  the hook gets switched off.
- **Regular expression over the raw command string.** Misses `sudo git …` and `bash -c`, and flags `git commit -m "…reset --hard…"`.
- **A full shell parser (a library such as bashlex).** Adds a dependency (ADR 0002) and still cannot resolve variables or
  `base64 | sh`, so the guarantee would be no stronger than the scanner's.
- **Fail closed on parse errors.** Safer in the abstract; in practice it stops work for reasons the user cannot see.
- **Authorization by conversation ("yes, you may").** Forgotten by the next session and invisible in review; a committed
  line is neither.

## Consequences

Obfuscated commands (variables, encoded payloads, scripts written then run) are not caught. That is documented, and
is why real boundaries (permissions, sandboxes, branch protection) stay in place underneath.
