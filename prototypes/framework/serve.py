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
import re
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


def weights(accept: str) -> dict[str, float]:
    """`Accept-Encoding` as coding → weight, tokens and parameters read
    without regard to case (RFC 9110 §12.5.3; PROTO-2-12)."""
    out: dict[str, float] = {}
    for part in accept.split(","):
        token, *params = [x.strip() for x in part.split(";")]
        if not token:
            continue
        q = 1.0
        for param in params:
            name, _, value = param.partition("=")
            if name.strip().lower() == "q":
                try:
                    q = float(value)
                except ValueError:
                    q = 0.0
        out[token.lower()] = q
    return out


def acceptable(accept: str, coding: str) -> float:
    w = weights(accept)
    star = w.get("*")
    if coding in w:
        return w[coding]
    if coding == "identity":  # identity is acceptable unless excluded, by name or by `*;q=0`
        return star if star is not None else 1.0
    return star if star is not None else 0.0


def negotiate(accept: str, *, compressible: bool = True) -> str | None:
    """The representation to send — "br", "gzip" or "identity" — or None when
    the request accepts none of them, which is answered 406: the compressed
    coding of the highest weight, Brotli on a tie, unless identity is weighed
    higher (PROTO-1-15, PROTO-2-12)."""
    identity = acceptable(accept, "identity")
    if compressible:
        ranked = sorted(((acceptable(accept, c), c != "br", c) for c in ("br", "gzip")), key=lambda x: (-x[0], x[1]))
        best_q, _, best = ranked[0]
        if best_q > 0 and not ("identity" in weights(accept) and identity > best_q):
            return best
    return "identity" if identity > 0 else None


def none_match(header: str | None, etag: str) -> bool:
    """`If-None-Match` against the selected representation's validator: `*`,
    or a list of entity tags compared weakly — a `W/` prefix ignored on either
    side (RFC 9110 §13.1.2, §8.8.3.2; PROTO-3-14)."""
    if header is None:
        return False
    if header.strip() == "*":
        return True
    opaque = etag[2:] if etag.startswith("W/") else etag
    for tag in _ETAG_LIST.findall(header):
        if (tag[2:] if tag.startswith("W/") else tag) == opaque:
            return True
    return False


_ETAG_LIST = re.compile(r'(?:W/)?"[^"]*"')


def _encode(data: bytes, coding: str) -> tuple[bytes, str | None]:
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
            accept = ", ".join(self.headers.get_all("Accept-Encoding") or [])  # every field line, in order (RFC 9110 §5.2; PROTO-5-10)
            coding = negotiate(accept, compressible=suffix in TEXT)
            if coding is None:
                self.send_response(406)
                self.send_header("Content-Length", "0")
                self.send_header("Vary", "Accept-Encoding")
                self.end_headers()
                log.append({"path": path, "status": 406})
                return
            data, encoding = _encode(data, coding)
            etag = '"' + hashlib.sha256(data + b"\0" + (encoding or "identity").encode()).hexdigest() + '"'
            lines = self.headers.get_all("If-None-Match")  # every field line, in order (RFC 9110 §5.2; PROTO-4-10)
            if none_match(", ".join(lines) if lines else None, etag):
                # No Content-Length: on a 304 it would describe the 200 it
                # stands for, and a body is never sent (RFC 9110 §8.6, §15.4.5;
                # PROTO-3-14).
                self.send_response(304)
                self._common(etag, encoding, suffix)
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
