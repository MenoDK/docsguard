# 0004. Tokens are estimated as characters divided by four

Status: Accepted

## Context

The instruction budget and `docsguard budget` need a size in tokens: what a session pays before the first question, and
what it would pay reading every document. The number is used to set budgets and to compare ("2k versus 30k"), never
to bill. It must be computable offline, in CI, with no account and no dependency.

## Decision

`estimate_tokens(text) = ceil(len(text) / 4)`, labelled as an estimate everywhere it is printed ("characters / 4: good
for budgeting, not for billing"). Per-file line caps are enforced in lines, which are exact.

## Rejected alternatives

- **A tokenizer library.** A dependency (ADR 0002), tied to one model family's vocabulary, and still approximate for another.
- **The provider's token-counting endpoint.** Exact, but needs network, credentials and a paid call in CI, and would make
  the guard flaky for forks and offline work.
- **Words times a constant.** No better than characters, and worse for code and tables.

## Consequences

Error of tens of percent is expected, more for code and non-English text. That is acceptable for a budget whose purpose is to
tell 800 tokens from 8,000. If a budget is ever tight enough for the error to matter, the budget is the problem.
