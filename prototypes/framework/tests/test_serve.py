"""The local server of §2.7: content negotiation by weight and one strong
validator per representation (PROTO-1-15)."""

from __future__ import annotations

import gzip
import urllib.request

import brotli
import pytest

import serve


@pytest.mark.parametrize("accept, coding", [
    ("", "identity"), ("identity", "identity"), ("gzip", "gzip"), ("br, gzip", "br"), ("gzip, br", "br"),
    ("br;q=0, gzip;q=1", "gzip"), ("br;q=0.5, gzip;q=0.8", "gzip"), ("*", "br"), ("*;q=0, identity", "identity"),
    ("br;q=0, gzip;q=0", "identity"), ("br;Q=0,gzip", "gzip"), ("BR;q=0, GZIP", "gzip"),
    ("br;q=0, gzip;q=0, identity;q=0", None), ("*;q=0", None), ("identity;q=1, gzip;q=0.5", "identity"),
])
def test_negotiation_honours_the_weights(accept, coding):
    assert serve.negotiate(accept) == coding


def _get(url, accept, etag=None):
    headers = {"Accept-Encoding": accept} | ({"If-None-Match": etag} if etag else {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_each_representation_has_its_own_validator(tmp_path):
    (tmp_path / "app.js").write_text("export const v = 1;\n" * 50)
    with serve.Server(tmp_path) as s:
        url = s.url + "app.js"
        plain = _get(url, "identity")
        zipped = _get(url, "br;q=0, gzip")
        brot = _get(url, "br")
        assert plain[1].get("Content-Encoding") is None and zipped[1]["Content-Encoding"] == "gzip" and brot[1]["Content-Encoding"] == "br"
        assert gzip.decompress(zipped[2]) == plain[2] == brotli.decompress(brot[2])
        assert len({plain[1]["ETag"], zipped[1]["ETag"], brot[1]["ETag"]}) == 3
        assert all(r[1]["Vary"] == "Accept-Encoding" and r[1]["Cache-Control"] == "no-cache" for r in (plain, zipped, brot))
        assert _get(url, "br;q=0, gzip", zipped[1]["ETag"])[0] == 304
        assert _get(url, "br", zipped[1]["ETag"])[0] == 200  # another representation's validator is not this one's


def test_a_request_that_accepts_no_representation_is_refused(tmp_path):
    (tmp_path / "app.js").write_text("export const v = 1;\n")
    (tmp_path / "x.bice").write_bytes(b"\x00\x01")
    with serve.Server(tmp_path) as s:
        for accept in ("br;q=0, gzip;q=0, identity;q=0", "*;q=0"):
            assert _get(s.url + "app.js", accept)[0] == 406
        assert _get(s.url + "x.bice", "identity;q=0")[0] == 406
        assert _get(s.url + "x.bice", "gzip")[0] == 200  # a binary is sent as it is, which identity allows


def test_a_conditional_get_matches_weakly_and_lists_and_sends_no_length(tmp_path):
    """PROTO-3-14: weak comparison, a list of validators and `*`; a 304 never
    carries a length that is not the 200's."""
    (tmp_path / "app.js").write_text("export const v = 1;\n" * 50)
    with serve.Server(tmp_path) as s:
        url = s.url + "app.js"
        zipped = _get(url, "br;q=0, gzip")
        tag = zipped[1]["ETag"]
        for header in (tag, "W/" + tag, f'"other", {tag}', f'W/"x",W/{tag}', "*"):
            status, headers, body = _get(url, "br;q=0, gzip", header)
            assert status == 304 and body == b"", header
            assert headers.get("Content-Length") in (None, zipped[1]["Content-Length"]), header
        assert _get(url, "br", tag)[0] == 200  # Brotli's representation does not match gzip's validator
        assert _get(url, "br;q=0, gzip", '"other"')[0] == 200
        assert serve.none_match(None, tag) is False
