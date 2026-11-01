from __future__ import annotations

from pathlib import Path

import pytest

from docsguard.rules.secrets import PATTERNS, scan_text

from .conftest import findings, result, write

# Built at run time: this file must not contain a string that looks like a credential, or the repository's own
# secret scanner would (rightly) flag the test that checks the scanner.
GITHUB = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
AWS = "AK" + "IA" + "Q3W4E5R6T7Y8U9I0"
SLACK = "xo" + "xb-" + "1234567890-abcdefghij"
JWT = "ey" + "J" + "hbGciOiJIUzI1NiJ9." + "ey" + "J" + "zdWIiOiIxMjM0NTY3ODkwIn0." + "abcdefghij1234567890"
PRIVATE_KEY = "-----BEGIN " + "RSA PRIVATE KEY" + "-----"
LONG_VALUE = "k3Jf9Zq1Xw8Lm2Np7Vb4"


@pytest.mark.parametrize(
    ("line", "name"),
    [
        pytest.param(f"token {GITHUB}", "GitHub token", id="github-token"),
        pytest.param(f"key {AWS}", "AWS access key id", id="aws-access-key"),
        pytest.param(f"hook {SLACK}", "Slack token", id="slack-token"),
        pytest.param(f"bearer {JWT}", "JSON web token", id="jwt"),
        pytest.param(PRIVATE_KEY, "private key block", id="private-key-block"),
        pytest.param(f"password: {LONG_VALUE}", "secret assignment", id="assignment-yaml"),
        pytest.param(f'"api_key": "{LONG_VALUE}"', "secret assignment", id="assignment-json"),
        pytest.param(f"postgres://admin:{LONG_VALUE}@db.internal/app", "credential in a URL", id="url-credential"),
        pytest.param("host prod-db.abc123xyz.us-east-1.rds.amazonaws.com", "managed database host", id="rds-host"),
        pytest.param("arn:aws:iam::123456789012:role/deploy", "cloud account id in an ARN", id="arn-account-id"),
    ],
)
def test_each_pattern_is_detected(line: str, name: str) -> None:
    assert [n for _, n in scan_text(line)] == [name]


@pytest.mark.parametrize(
    "line",
    [
        "password: changeme-changeme-changeme",
        "password: <your-password-here-please>",
        "api_key: ${API_KEY_FROM_ENVIRONMENT}",
        "token = your_token_goes_right_here",
        "secret: example-example-example-example",
        "postgres://user:password@localhost/db",  # short, obvious placeholder value
        "AKIAIOSFODNN7EXAMPLE",  # AWS's own documentation key
        "No credentials here, just prose about passwords and tokens.",
    ],
)
def test_obvious_placeholders_and_prose_are_not_flagged(line: str) -> None:
    assert scan_text(line) == []


def test_a_real_key_on_a_line_that_says_for_example_is_still_reported() -> None:
    assert [n for _, n in scan_text(f"for example, use {GITHUB}")] == ["GitHub token"]


def test_the_report_names_the_pattern_and_the_line_but_never_the_secret(repo_dir: Path) -> None:
    write(repo_dir, "docs/notes.md", f"# Notes\n\nthe token is {GITHUB}\n")
    found = findings(repo_dir, "no-secrets")
    assert [(f.path, f.line) for f in found] == [("docs/notes.md", 3)]
    assert "GitHub token" in found[0].message
    assert GITHUB not in found[0].render() and GITHUB[:8] not in found[0].render()


def test_secrets_are_looked_for_in_claude_configuration_too(repo_dir: Path) -> None:
    write(repo_dir, ".claude/settings.json", '{"env": {"password": "' + LONG_VALUE + '"}}\n')
    assert [f.path for f in findings(repo_dir, "no-secrets")] == [".claude/settings.json"]


def test_code_outside_docs_and_claude_is_not_this_rules_job(repo_dir: Path) -> None:
    write(repo_dir, "src/app.py", f"TOKEN = '{GITHUB}'\n")
    assert findings(repo_dir, "no-secrets") == []


def test_the_rule_reports_how_many_files_it_looked_at(repo_dir: Path) -> None:
    assert result(repo_dir, "no-secrets").examined >= 15


def test_there_are_patterns_for_every_family_the_tests_cover() -> None:
    assert len(PATTERNS) == 9
