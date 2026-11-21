"""The local static server of stage 2.3 (docs/framework_prototype.md §2.7).

One server for both candidates, on 127.0.0.1: `firebase.json`'s headers on
every file, text compressed with brotli or gzip as the request accepts, with
`Vary: Accept-Encoding`, and a strong `ETag` per representation — the SHA-256
of the bytes sent and their encoding —, so that revalidations behave as on a
host. It serves an artifact folder and nothing outside it.
"""

from __future__ import annotations

import gzip
import hashlib
import http.server
import json
import mimetypes
import pathlib
import threading
import urllib.parse

REPO = pathlib.Path(__file__).resolve().parents[2]
TEXT = (".html", ".js", ".mjs", ".css", ".json", ".svg", ".txt", ".md", ".map", ".wasm")
TYPES = {".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm", ".bice": "application/octet-stream",
         ".json": "application/json", ".md": "text/markdown", ".parquet": "application/octet-stream", ".arrow": "application/octet-stream"}


def hosting_headers() -> list[tuple[str, str]]:
    config = json.loads((REPO / "firebase.json").read_text(encoding="utf-8"))
    out = []
    for rule in config["hosting"].get("headers", []):
        if rule.get("source") == "**":
            out += [(h["key"], h["value"]) for h in rule["headers"]]
    return out


def negotiate(accept: str) -> str | None:
    """The encoding the request accepts with the highest weight — `br`, then
    `gzip`, then identity on a tie —, honouring `q=0` and `*` (RFC 9110
    §12.5.3; PROTO-1-15). `None` is identity."""
    weights: dict[str, float] = {}
    for part in accept.split(","):
        token, *params = [x.strip() for x in part.split(";")]
        if not token:
            continue
        q = 1.0
        for param in params:
            if param.startswith("q="):
                try:
                    q = float(param[2:])
                except ValueError:
                    q = 0.0
        weights[token.lower()] = q
    star = weights.get("*")

    def weight(coding: str) -> float:
        return weights.get(coding, star if star is not None else 0.0)

    compressed = sorted((c for c in ("br", "gzip") if weight(c) > 0), key=lambda c: (-weight(c), c != "br"))
    explicit_identity = weights.get("identity")
    if compressed and not (explicit_identity is not None and explicit_identity > weight(compressed[0])):
        return compressed[0]
    return None  # identity: what is sent when no compressed coding is preferred


def _encode(data: bytes, accept: str) -> tuple[bytes, str | None]:
    coding = negotiate(accept)
    if coding == "br":
        import brotli

        return brotli.compress(data), "br"
    if coding == "gzip":
        return gzip.compress(data, mtime=0), "gzip"
    return data, None


def handler_for(root: pathlib.Path):
    root = root.resolve()
    headers = hosting_headers()
    log: list[dict] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):  # noqa: N802
            path = urllib.parse.urlsplit(self.path).path
            rel = urllib.parse.unquote(path).lstrip("/") or "index.html"
            if rel.endswith("/"):
                rel += "index.html"
            target = (root / rel).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                log.append({"path": path, "status": 404})
                return
            data = target.read_bytes()
            suffix = target.suffix.lower()
            encoding = None
            if suffix in TEXT:
                data, encoding = _encode(data, self.headers.get("Accept-Encoding", ""))
            etag = '"' + hashlib.sha256(data + b"\0" + (encoding or "identity").encode()).hexdigest() + '"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self._common(etag, encoding, suffix)
                self.send_header("Content-Length", "0")
                self.end_headers()
                log.append({"path": path, "status": 304, "encoding": encoding, "etag": etag})
                return
            self.send_response(200)
            self._common(etag, encoding, suffix)
            self.send_header("Content-Type", TYPES.get(suffix) or mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            log.append({"path": path, "status": 200, "encoding": encoding, "bytes": len(data), "etag": etag})

        def _common(self, etag, encoding, suffix):
            for key, value in headers:
                self.send_header(key, value)
            self.send_header("ETag", etag)
            if suffix in TEXT:
                self.send_header("Vary", "Accept-Encoding")
            if encoding:
                self.send_header("Content-Encoding", encoding)

    return Handler, log


class Server:
    """`with Server(artifact) as s: s.url` — a thread on an ephemeral port."""

    def __init__(self, root: pathlib.Path, port: int = 0):
        handler, self.log = handler_for(root)
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/"

    def __enter__(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
