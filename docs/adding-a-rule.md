# Adding a guard

A guard is finished when its mutant dies. In this order:

1. **Write the failing test first** in the matching `tests/test_*.py`, built on the `repo_dir` fixture (the initialised
   template: a known-good repository). Break one thing per test and assert the *finding*, with path and line, not just "not ok".
2. **Implement the rule** in `src/docsguard/rules/` as `def rule(repo, config) -> RuleResult`. Return `examined` honestly,
   and `skipped="why"` when it does not apply; never pass silently on zero items (ADR 0005).
3. **Register it** in `checks.RULES` with a one-line statement of what a failure means.
4. **Add a mutant** to `scripts/sabotage.py` that deletes the decision, and run it:
   `python scripts/sabotage.py -k "your rule"`. It must report `killed … by <a test>`. `INVALID` means the mutant did not
   run (a syntax error), `SURVIVED` means the test is weaker than the rule.
5. **Give the template real input** for it, so `test_every_guard_examined_something_on_the_template` stays true.
6. **Document it**: a row in `docs/TECHNIQUES.md` if it is a new technique, an ADR if it was a decision with alternatives.
