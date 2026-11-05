"""The playground's web server: the site, and a small JSON API over the real guards. Standard library only.

Two checks keep a web page from driving it, and neither is authentication: the Host header must be a name the server
answers to (a DNS-rebinding page arrives with the attacker's name), and a request that changes something must come from
this origin or from no browser at all. The lab, the endpoints that change the sample, answers 404 unless it was asked
for, and the server refuses to start with it on when it is told it is in production.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar, Final
from urllib.parse import unquote, urlsplit

from docsguard import __version__

from .lab import BreakError, Lab, LabError

# The page's scripts and styles are all same-origin files: nothing inline, nothing from elsewhere.
CSP: Final = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
MAX_BODY: Final = 4096
DRAIN_LIMIT: Final = 65536
TIMEOUT: Final = 30  # seconds a client may stall, mid-request or between requests, before its connection is dropped
TYPES: Final = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
}
LOOPBACK: Final = frozenset({"localhost", "127.0.0.1", "[::1]"})


class ConfigError(ValueError):
    """The server was started in a way it refuses."""


@dataclass(frozen=True, slots=True)
class Settings:
    site_dir: Path
    allowed_hosts: frozenset[str] = LOOPBACK
    lab: bool = False
    production: bool = False

    def __post_init__(self) -> None:
        if self.lab and self.production:
            raise ConfigError("DG_LAB=1 is refused when DG_ENV=production: the lab has no authentication on purpose")


def settings_from_env(env: dict[str, str] | None = None) -> Settings:
    """Read the DG_* variables. An empty value counts as unset, so a copied ``.env.example`` changes nothing."""
    env = dict(os.environ) if env is None else env
    extra = frozenset(h.strip().lower() for h in env.get("DG_ALLOWED_HOSTS", "").split(",") if h.strip())
    default_site = Path(__file__).resolve().parent.parent / "site"
    return Settings(
        site_dir=Path(env.get("DG_SITE_DIR") or default_site),
        allowed_hosts=LOOPBACK | extra,
        lab=env.get("DG_LAB", "").strip().lower() in ("1", "true"),
        production=env.get("DG_ENV", "").strip().lower() == "production",
    )


def address_from_env(env: dict[str, str] | None = None) -> tuple[str, int]:
    """Where to listen. The default is the loopback; the image sets DG_BIND because a container needs 0.0.0.0."""
    env = dict(os.environ) if env is None else env
    host = env.get("DG_BIND") or "127.0.0.1"
    raw = env.get("DG_PORT") or "8200"
    if not raw.isdigit() or not 0 < int(raw) < 65536:
        raise ConfigError(f"DG_PORT must be a port number between 1 and 65535, not {raw!r}")
    return host, int(raw)


Answer = tuple[int, dict[str, Any]]


class App:
    """Routes, kept apart from the socket code so they can be tested without a socket."""

    def __init__(self, settings: Settings, lab: Lab) -> None:
        self.settings = settings
        self.lab = lab

    # ------------------------------------------------------------------ routes

    def get(self, path: str) -> Answer:
        match path:
            case "/api/health":
                return 200, {"ok": True, "lab": self.settings.lab, "version": __version__}
            case "/api/overview":
                return 200, {**self.lab.overview(), "lab": self.settings.lab, "version": __version__}
            case "/api/check":
                return 200, self.lab.check()
            case "/api/files":
                return 200, {"files": self.lab.files()}
            case "/api/budget":
                return 200, self.lab.budget()
        return 404, {"error": "not_found"}

    def post(self, path: str, body: dict[str, Any]) -> Answer:
        try:
            match path:
                case "/api/hooks/git":
                    return 200, self.lab.hook_git(_text(body, "command"))
                case "/api/hooks/scope":
                    return 200, self.lab.hook_scope(_text(body, "tool"), _text(body, "target"))
                case "/api/lab/break" | "/api/lab/authorize" | "/api/lab/reset":
                    if not self.settings.lab:
                        return 404, {"error": "not_found"}
                    return self._lab(path, body)
        except LabError as error:
            return 400, {"error": "bad_request", "issues": [str(error)]}
        except BreakError as error:
            return 500, {"error": "sample_changed", "issues": [str(error)]}
        return 404, {"error": "not_found"}

    def _lab(self, path: str, body: dict[str, Any]) -> Answer:
        if path == "/api/lab/reset":
            self.lab.reset()
            return 200, {"ok": True}
        if path == "/api/lab/break":
            on = body.get("on")
            if not isinstance(on, bool):
                raise LabError("'on' must be true or false")
            self.lab.set_break(_text(body, "id"), on)
            return 200, {"ok": True}
        line = self.lab.authorize(_text(body, "needle"), _text(body, "reason", required=False))
        return 200, {"ok": True, "line": line}

    # ------------------------------------------------------------------ gates

    def host_allowed(self, host_header: str | None) -> bool:
        host = (host_header or "").lower()
        # an IPv6 literal keeps its colons inside brackets: "[::1]:8200"
        name = host[: host.find("]") + 1] if host.startswith("[") else host.split(":", 1)[0]
        return name in self.settings.allowed_hosts

    @staticmethod
    def origin_allowed(origin: str | None, host_header: str | None, fetch_site: str | None) -> bool:
        if fetch_site == "cross-site":
            return False
        if origin is None:
            return True  # not a browser, or a same-origin navigation that does not send one
        try:
            origin_host = urlsplit(origin).netloc.lower()
        except ValueError:
            return False
        return origin_host != "" and origin_host == (host_header or "").lower()

    def static(self, path: str) -> tuple[int, bytes, str]:
        relative = unquote(path).lstrip("/") or "index.html"
        base = self.settings.site_dir.resolve()
        candidate = (base / relative).resolve()
        servable = (
            base in candidate.parents
            and candidate.is_file()
            and candidate.suffix in TYPES
            and not any(part.startswith(".") for part in candidate.relative_to(base).parts)
        )
        if not servable:
            return 404, b"not found", "text/plain; charset=utf-8"
        return 200, candidate.read_bytes(), TYPES[candidate.suffix]


def _text(body: dict[str, Any], key: str, *, required: bool = True) -> str:
    value = body.get(key, "" if not required else None)
    if not isinstance(value, str):
        raise LabError(f"'{key}' must be text")
    return value


def make_handler(app: App) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "docsguard-playground"
        sys_version = ""
        protocol_version = "HTTP/1.1"
        timeout = TIMEOUT
        routes: ClassVar[App] = app

        def log_message(self, format: str, *args: Any) -> None:
            return  # the demo prints nothing per request; the tests and the smoke script read the answers

        _body_read = False

        def handle_one_request(self) -> None:
            self._body_read = False  # one handler serves a whole keep-alive connection, one request at a time
            super().handle_one_request()

        # ------------------------------------------------------------ plumbing

        def _leaves_body_unread(self) -> bool:
            declared = (self.headers.get("Content-Length") or "").strip()
            return not self._body_read and (declared not in ("", "0") or bool(self.headers.get("Transfer-Encoding")))

        def _send(self, status: int, body: bytes, content_type: str, *, cache: str = "no-store") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            if self._leaves_body_unread():
                # Answering without reading the body would leave it in the stream, and the next request on this
                # connection would begin with it. Close the connection instead of guessing where the body ends.
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, data: dict[str, Any]) -> None:
            self._send(status, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

        def _gate(self, *, changes: bool) -> bool:
            if not app.host_allowed(self.headers.get("Host")):
                self._json(403, {"error": "host_not_allowed"})
                return False
            if changes and not app.origin_allowed(
                self.headers.get("Origin"), self.headers.get("Host"), self.headers.get("Sec-Fetch-Site")
            ):
                self._json(403, {"error": "origin_not_allowed"})
                return False
            return True

        def _take_body(self) -> bytes | None:
            """Read the whole declared body, or answer 400/413 and leave it unread (the connection is then closed)."""
            if self.headers.get("Transfer-Encoding"):
                self._json(400, {"error": "bad_request", "issues": ["chunked bodies are not accepted"]})
                return None
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                length = -1
            if length < 0:
                self._json(400, {"error": "bad_request", "issues": ["the Content-Length is not a number"]})
                return None
            if length > MAX_BODY:
                if length <= DRAIN_LIMIT:
                    # Throw a modest body away so the client reads the answer instead of a reset; a bigger one is
                    # not read at all, and the connection is closed.
                    self.rfile.read(length)
                    self._body_read = True
                self._json(413, {"error": "body_too_large"})
                return None
            raw = self.rfile.read(length)
            self._body_read = True
            return raw

        def _parse(self, raw: bytes) -> dict[str, Any] | None:
            kind = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if kind != "application/json":
                self._json(415, {"error": "unsupported_media_type"})
                return None
            try:
                data = json.loads(raw or b"{}")
            except ValueError:
                data = None
            if not isinstance(data, dict):
                self._json(400, {"error": "bad_request", "issues": ["the body must be a JSON object"]})
                return None
            return data

        # ------------------------------------------------------------ verbs

        def do_GET(self) -> None:
            self._serve()

        def do_HEAD(self) -> None:
            self._serve()

        def _serve(self) -> None:
            if not self._gate(changes=False):
                return
            path = urlsplit(self.path).path
            if path.startswith("/api/"):
                status, data = app.get(path)
                self._json(status, data)
                return
            status, body, kind = app.static(path)
            self._send(status, body, kind, cache="no-cache")

        def do_POST(self) -> None:
            raw = self._take_body()  # before anything is answered, so the stream stays in step
            if raw is None or not self._gate(changes=True):
                return
            path = urlsplit(self.path).path
            if not path.startswith("/api/"):
                self._json(404, {"error": "not_found"})
                return
            body = self._parse(raw)
            if body is None:
                return
            status, data = app.post(path, body)
            self._json(status, data)

        def _refuse(self) -> None:
            self._json(405, {"error": "method_not_allowed"})

        do_PUT = do_DELETE = do_PATCH = _refuse

    return Handler


def serve(
    settings: Settings, host: str, port: int, *, ready: Callable[[ThreadingHTTPServer], None] | None = None
) -> None:
    lab = Lab()
    server = ThreadingHTTPServer((host, port), make_handler(App(settings, lab)))
    server.daemon_threads = True
    if ready:
        ready(server)

    def stop(_signum: int, _frame: object) -> None:
        # shutdown() waits for serve_forever(), which is running in this thread: ask from another one
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        lab.close()


def main(argv: list[str] | None = None) -> int:
    del argv
    try:
        settings = settings_from_env()
        host, port = address_from_env()
    except ConfigError as error:
        print(f"docsguard playground: {error}", file=sys.stderr)
        return 2
    print(
        f"docsguard playground on http://{host}:{port} (lab {'on' if settings.lab else 'off'}); "
        "no login: it is a local tool, so publish it on the loopback only",
        flush=True,
    )
    serve(settings, host, port)
    return 0
