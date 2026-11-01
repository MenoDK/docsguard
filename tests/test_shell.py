from __future__ import annotations

from docsguard.hooks.shell import scan, simple_commands, strip_wrappers


def commands(text: str) -> list[list[str]]:
    return list(simple_commands(text))


def test_separators_split_commands_and_quotes_protect_them() -> None:
    assert [c[0] for c in commands("a; b && c || d | e & f\ng")] == list("abcdefg")
    assert commands("echo 'a; git reset --hard'") == [["echo", "a; git reset --hard"]]
    assert commands('echo "x && y"') == [["echo", "x && y"]]


def test_redirections_with_ampersands_do_not_hide_the_command() -> None:
    assert ["git", "push", "--force", "2>"] in commands("git push --force 2>&1")


def test_command_substitution_is_scanned_wherever_it_appears() -> None:
    assert ["git", "reset", "--hard"] in commands("echo $(git reset --hard)")
    assert ["git", "reset", "--hard"] in commands('echo "pre $(git reset --hard) post"')
    assert ["git", "reset", "--hard"] in commands("echo `git reset --hard`")
    assert ["git", "reset", "--hard"] in commands("echo $(echo $(git reset --hard))")


def test_single_quotes_prevent_substitution() -> None:
    assert commands("echo '$(git reset --hard)'") == [["echo", "$(git reset --hard)"]]


def test_heredoc_bodies_are_text_not_commands() -> None:
    script = "git commit -F - <<'EOF'\ngit reset --hard\nnotes\nEOF\ngit status"
    assert [c[:2] for c in commands(script)] == [["git", "commit"], ["git", "status"]]
    tabbed = "cat <<-END\n\tgit push --force\n\tEND\nls"
    assert [c[0] for c in commands(tabbed)] == ["cat", "ls"]


def test_wrappers_are_stripped_so_the_real_command_is_seen() -> None:
    assert strip_wrappers(["sudo", "-u", "root", "git", "status"]) == ["git", "status"]
    assert strip_wrappers(["env", "FOO=1", "-i", "git", "status"]) == ["git", "status"]
    assert strip_wrappers(["FOO=1", "BAR=2", "git", "status"]) == ["git", "status"]
    assert strip_wrappers(["timeout", "30", "git", "status"]) == ["git", "status"]
    assert strip_wrappers(["nice", "-n", "5", "git", "status"]) == ["git", "status"]
    assert strip_wrappers(["xargs", "-n", "1", "git", "status"]) == ["git", "status"]
    assert strip_wrappers(["then", "nohup", "git", "status"]) == ["git", "status"]
    assert strip_wrappers(["sudo", "env", "A=1", "timeout", "5", "git", "x"]) == ["git", "x"]


def test_shell_dash_c_and_eval_are_followed() -> None:
    assert ["git", "reset", "--hard"] in commands("bash -c 'git reset --hard'")
    assert ["git", "reset", "--hard"] in commands('sudo sh -lc "git reset --hard"')
    assert ["git", "reset", "--hard"] in commands("eval git reset --hard")
    assert ["git", "reset", "--hard"] in commands('bash -c "echo hi; git reset --hard"')


def test_a_script_file_is_not_expanded() -> None:
    assert commands("bash deploy.sh") == [["bash", "deploy.sh"]]


def test_unbalanced_quotes_do_not_crash_and_are_still_examined() -> None:
    assert any(c[:2] == ["git", "push"] for c in commands("git push --force 'oops"))


def test_deeply_nested_substitution_stops_instead_of_recursing_forever() -> None:
    text = "x"
    for _ in range(40):
        text = f"echo $({text})"
    assert isinstance(commands(text), list)


def test_scan_returns_nested_bodies_separately() -> None:
    segments, nested = scan("a $(b c) d")
    assert segments == ["a   d"] and nested == ["b c"]
