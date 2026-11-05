# Decision records

Each record states the problem, what was chosen, **what was rejected and why**, and the cost that was accepted.
Written before the implementation, so each is a decision and not a justification.

| # | Decision |
| --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions |
| [0002](0002-standard-library-only.md) | Standard library only at run time |
| [0003](0003-hooks-denylist-and-fail-open.md) | Hooks are a denylist, fail open, and are not a security boundary |
| [0004](0004-token-estimate-by-characters.md) | Tokens are estimated as characters divided by four |
| [0005](0005-a-guard-that-examines-nothing-fails.md) | A guard that examined nothing fails |
| [0006](0006-dismissals-carry-reasons-and-expire.md) | Every dismissal carries a written reason, and stale ones are reported |
| [0007](0007-the-playground-runs-the-real-guards-and-executes-nothing.md) | The playground runs the real guards on a sample it owns and executes nothing it is given |

New record: copy the shape of `0001`, take the next number, add a row here and bump the count in the map, in one commit.
