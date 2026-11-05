"""The playground's server, over a real socket: what it serves, what it refuses, and the lab off unless asked for."""

from __future__ import annotations

import http.client
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from playground.lab import Lab
from playground.server import (
    CSP,
    DRAIN_LIMIT,
    MAX_BODY,
    App,
    ConfigError,
    Settings,
    address_from_env,
    make_handler,
    settings_from_env,
)


@dataclass
class Running:
    port: int
    site: Path

    def call(
        self,
        method: str,
        path: str,
        body: object | None = None,
        headers: dict[str, str] | None = None,
        raw: bytes | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        sent = {"Host": f"localhost:{self.port}", **(headers or {})}
        payload = raw
        if body is not None:
            payload = json.dumps(body).encode()
            sent.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=payload, headers=sent)
        response = conn.getresponse()
        data = response.read()
        result = (response.status, {k.lower(): v for k, v in response.getheaders()}, data)
        conn.close()
        return result

    def json(self, method: str, path: str, body: object | None = None, **kw: object) -> tuple[int, dict[str, object]]:
        status, _, data = self.call(method, path, body, **kw)  # type: ignore[arg-type]
        return status, json.loads(data)


def start(site: Path, *, lab: bool, extra_hosts: frozenset[str] = frozenset()) -> Iterator[Running]:
    settings = Settings(
        site_dir=site, allowed_hosts=frozenset({"localhost", "127.0.0.1", "[::1]"}) | extra_hosts, lab=lab
    )
    sandbox = Lab()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(App(settings, sandbox)))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield Running(server.server_address[1], site)
    finally:
        server.shutdown()
        server.server_close()
        sandbox.close()


@pytest.fixture
def site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    (root / "i18n").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (root / "kit.js").write_text("// kit", encoding="utf-8")
    (root / "i18n" / "pt.js").write_text("// pt", encoding="utf-8")
    (root / "notes.txt").write_text("not a site file", encoding="utf-8")
    (root / ".hidden.js").write_text("// hidden", encoding="utf-8")
    (tmp_path / "outside.js").write_text("// outside the site", encoding="utf-8")
    return root


@pytest.fixture
def server(site: Path) -> Iterator[Running]:
    yield from start(site, lab=True)


@pytest.fixture
def server_without_lab(site: Path) -> Iterator[Running]:
    yield from start(site, lab=False)


# --------------------------------------------------------------------------------------------------- serving


def test_the_site_is_served_with_a_strict_policy_on_every_response(server: Running) -> None:
    for path in ("/", "/kit.js", "/api/health", "/nothing-here"):
        status, headers, _ = server.call("GET", path)
        assert status in (200, 404)
        assert headers["content-security-policy"] == CSP
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"


def test_the_root_is_the_index_and_nested_site_files_are_served(server: Running) -> None:
    assert server.call("GET", "/")[2].startswith(b"<!doctype html>")
    assert server.call("GET", "/i18n/pt.js")[0] == 200


def test_head_answers_without_a_body(server: Running) -> None:
    status, headers, body = server.call("HEAD", "/kit.js")
    assert status == 200
    assert body == b""
    assert int(headers["content-length"]) == len("// kit")


@pytest.mark.parametrize(
    "path",
    [
        "/../outside.js",
        "/%2e%2e/outside.js",
        "/i18n/../../outside.js",
        "/.hidden.js",
        "/notes.txt",
        "/i18n/",
        "//etc/passwd",
    ],
)
def test_nothing_outside_the_site_and_no_odd_file_is_served(server: Running, path: str) -> None:
    assert server.call("GET", path)[0] == 404


@pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
def test_other_methods_are_refused(server: Running, method: str) -> None:
    assert server.call(method, "/api/health")[0] == 405


# --------------------------------------------------------------------------------------------------- the two gates


def test_a_foreign_host_is_refused_for_the_api_and_for_the_site(server: Running) -> None:
    for path in ("/api/health", "/"):
        status, _, body = server.call("GET", path, headers={"Host": "evil.example"})
        assert status == 403
        assert json.loads(body) == {"error": "host_not_allowed"}


def test_a_look_alike_host_is_refused(server: Running) -> None:
    for host in ("localhost.evil.example", "evil.example:8200", "127.0.0.1.evil.example", ""):
        assert server.call("GET", "/api/health", headers={"Host": host})[0] == 403


def test_the_loopback_names_are_allowed_with_or_without_a_port(server: Running) -> None:
    for host in ("localhost", "localhost:8200", "127.0.0.1:8200", "[::1]:8200", "LOCALHOST:8200"):
        assert server.call("GET", "/api/health", headers={"Host": host})[0] == 200


def test_an_extra_host_can_be_added_by_name_only(site: Path) -> None:
    for running in start(site, lab=False, extra_hosts=frozenset({"playground"})):
        assert running.call("GET", "/api/health", headers={"Host": "playground:8200"})[0] == 200
        assert running.call("GET", "/api/health", headers={"Host": "other:8200"})[0] == 403


def test_a_request_that_changes_something_must_come_from_this_origin(server: Running) -> None:
    body = {"id": "orphan-doc", "on": True}
    foreign = {"Origin": "https://evil.example"}
    assert server.json("POST", "/api/lab/break", body, headers=foreign)[0] == 403
    assert server.json("POST", "/api/lab/break", body, headers={"Origin": "null"})[0] == 403
    assert server.json("POST", "/api/lab/break", body, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    own = {"Origin": f"http://localhost:{server.port}"}
    assert server.json("POST", "/api/lab/break", body, headers=own)[0] == 200
    assert server.json("POST", "/api/lab/break", body)[0] == 200  # no browser, no Origin: a script or a test


def test_the_origin_gate_does_not_stop_a_plain_read(server: Running) -> None:
    assert server.call("GET", "/api/health", headers={"Origin": "https://evil.example"})[0] == 200


# --------------------------------------------------------------------------------------------------- bodies


def test_a_body_must_be_json_and_small_and_an_object(server: Running) -> None:
    assert server.call("POST", "/api/hooks/git", raw=b"command=git", headers={"Content-Type": "text/plain"})[0] == 415
    big = b'{"command": "' + b"x" * MAX_BODY + b'"}'
    assert server.call("POST", "/api/hooks/git", raw=big, headers={"Content-Type": "application/json"})[0] == 413
    for raw in (b"{not json", b"[1, 2]", b'"text"'):
        assert server.call("POST", "/api/hooks/git", raw=raw, headers={"Content-Type": "application/json"})[0] == 400


# --------------------------------------------------------------------------------------------------- keep-alive


def _ask(
    conn: http.client.HTTPConnection, method: str, path: str, body: bytes | None = None, **headers: str
) -> tuple[int, dict[str, str], bytes]:
    sent = {"Host": f"localhost:{conn.port}", "Content-Type": "application/json", **headers}
    conn.request(method, path, body=body, headers=sent)
    response = conn.getresponse()
    return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()


def test_a_refused_post_does_not_poison_the_connection_it_arrived_on(server: Running) -> None:
    # A browser reuses one connection for many requests. Answering 403 without reading the body would leave the body
    # in the stream, and the next request would be parsed from the middle of it.
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    body = json.dumps({"id": "orphan-doc", "on": True}).encode()
    for refused in ({"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
        status, headers, _ = _ask(conn, "POST", "/api/lab/break", body, **refused)
        assert status == 403
        # the body was read before the refusal was sent, so there is nothing left in the stream to close over
        assert "close" not in headers.get("connection", "")
    status, headers, data = _ask(conn, "GET", "/api/health")
    assert (status, json.loads(data)["ok"]) == (200, True)
    assert "close" not in headers.get("connection", "")
    conn.close()


def test_a_body_that_is_read_keeps_the_connection_open(server: Running) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    for _ in range(3):
        status, headers, _ = _ask(conn, "POST", "/api/hooks/git", b'{"command": "git status"}')
        assert status == 200
        assert "close" not in headers.get("connection", "")
    conn.close()


def test_a_body_over_the_limit_gets_its_413_and_the_connection_still_works(server: Running) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    assert _ask(conn, "POST", "/api/hooks/git", b"x" * (MAX_BODY + 1000))[0] == 413
    assert _ask(conn, "GET", "/api/health")[0] == 200
    conn.close()


def test_a_body_too_big_to_throw_away_is_not_read_and_the_connection_is_closed(server: Running) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    conn.putrequest("POST", "/api/hooks/git", skip_host=True)
    for name, value in (("Host", f"localhost:{server.port}"), ("Content-Type", "application/json")):
        conn.putheader(name, value)
    conn.putheader("Content-Length", str(DRAIN_LIMIT * 100))  # promised, never sent
    conn.endheaders()
    response = conn.getresponse()
    assert response.status == 413
    assert response.getheader("Connection") == "close"
    conn.close()


@pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
def test_a_refused_method_with_a_body_closes_the_connection(server: Running, method: str) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    status, headers, _ = _ask(conn, method, "/api/health", b'{"a": 1}')
    assert status == 405
    assert headers["connection"] == "close"
    conn.close()


def test_a_get_that_carries_a_body_is_answered_and_the_connection_closed(server: Running) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    status, headers, _ = _ask(conn, "GET", "/api/health", b'{"a": 1}')
    assert status == 200
    assert headers["connection"] == "close"
    conn.close()


def test_a_chunked_body_is_refused_rather_than_misread(server: Running) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    conn.putrequest("POST", "/api/hooks/git", skip_host=True)
    for name, value in (
        ("Host", f"localhost:{server.port}"),
        ("Content-Type", "application/json"),
        ("Transfer-Encoding", "chunked"),
    ):
        conn.putheader(name, value)
    conn.endheaders(b"5\r\nhello\r\n0\r\n\r\n", encode_chunked=False)
    response = conn.getresponse()
    assert response.status == 400
    assert response.getheader("Connection") == "close"
    conn.close()


def test_a_field_of_the_wrong_type_is_a_400_not_a_crash(server: Running) -> None:
    status, data = server.json("POST", "/api/hooks/git", {"command": 5})
    assert status == 400
    assert data["error"] == "bad_request"
    assert server.json("POST", "/api/lab/break", {"id": "orphan-doc", "on": "yes"})[0] == 400
    assert server.json("POST", "/api/lab/break", {"id": "nope", "on": True})[0] == 400


# --------------------------------------------------------------------------------------------------- the lab


def test_the_lab_answers_404_unless_it_was_asked_for(server_without_lab: Running) -> None:
    for path, body in (
        ("/api/lab/break", {"id": "orphan-doc", "on": True}),
        ("/api/lab/authorize", {"needle": ".env", "reason": "a reason long enough"}),
        ("/api/lab/reset", {}),
    ):
        assert server_without_lab.json("POST", path, body)[0] == 404
    status, data = server_without_lab.json("GET", "/api/overview")
    assert status == 200
    assert data["lab"] is False
    assert server_without_lab.json("GET", "/api/check")[1]["ok"] is True  # still untouched


def test_what_only_reads_works_with_the_lab_off(server_without_lab: Running) -> None:
    assert server_without_lab.json("POST", "/api/hooks/git", {"command": "git reset --hard"})[1]["allowed"] is False
    assert server_without_lab.json("GET", "/api/budget")[0] == 200
    assert server_without_lab.json("GET", "/api/files")[0] == 200


def test_the_lab_refuses_to_start_in_production() -> None:
    with pytest.raises(ConfigError):
        settings_from_env({"DG_LAB": "1", "DG_ENV": "production"})
    assert settings_from_env({"DG_ENV": "production"}).lab is False
    assert settings_from_env({"DG_LAB": "1"}).lab is True


@pytest.mark.parametrize("spelling", ["production", "Production", "PRODUCTION", " production "])
def test_production_is_recognised_however_it_is_spelled(spelling: str) -> None:
    with pytest.raises(ConfigError):
        settings_from_env({"DG_LAB": "1", "DG_ENV": spelling})


def test_an_empty_variable_counts_as_unset_so_a_copied_env_example_changes_nothing(tmp_path: Path) -> None:
    blank = {"DG_PORT": "", "DG_BIND": "", "DG_SITE_DIR": "", "DG_ALLOWED_HOSTS": "", "DG_LAB": "", "DG_ENV": ""}
    settings = settings_from_env(blank)
    assert settings.site_dir.name == "site"
    assert settings.lab is False
    assert settings.production is False
    assert settings.allowed_hosts == {"localhost", "127.0.0.1", "[::1]"}
    assert address_from_env(blank) == ("127.0.0.1", 8200)
    assert settings_from_env({"DG_SITE_DIR": str(tmp_path)}).site_dir == tmp_path


@pytest.mark.parametrize("port", ["abc", "0", "65536", "-1", "80.5", "8 0"])
def test_a_port_that_is_not_a_port_is_refused_before_anything_starts(port: str) -> None:
    with pytest.raises(ConfigError):
        address_from_env({"DG_PORT": port})


def test_the_address_is_the_loopback_unless_the_image_says_otherwise() -> None:
    assert address_from_env({}) == ("127.0.0.1", 8200)
    assert address_from_env({"DG_BIND": "0.0.0.0", "DG_PORT": "9000"}) == ("0.0.0.0", 9000)  # noqa: S104


def test_extra_hosts_come_from_the_environment_as_names_only() -> None:
    settings = settings_from_env({"DG_ALLOWED_HOSTS": " Playground , other ,"})
    assert {"playground", "other", "localhost"} <= settings.allowed_hosts


def test_breaking_the_sample_and_starting_over_through_the_api(server: Running) -> None:
    assert server.json("GET", "/api/check")[1]["ok"] is True
    assert server.json("POST", "/api/lab/break", {"id": "secret", "on": True})[0] == 200
    status, report = server.json("GET", "/api/check")
    assert status == 200
    assert report["ok"] is False
    assert "AKIA" not in json.dumps(report)
    assert server.json("POST", "/api/lab/reset", {})[0] == 200
    assert server.json("GET", "/api/check")[1]["ok"] is True


def test_the_overview_lists_every_break_and_every_guard(server: Running) -> None:
    _, data = server.json("GET", "/api/overview")
    assert isinstance(data["breaks"], list)
    assert len(data["breaks"]) == 10
    assert isinstance(data["rules"], list)
    assert len(data["rules"]) == 9
    assert data["sample"] == "sample-shop"
