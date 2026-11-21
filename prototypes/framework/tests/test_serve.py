"""The local server of §2.7: content negotiation by weight and one strong
validator per representation (PROTO-1-15)."""

from __future__ import annotations

import gzip
import urllib.request

import brotli
import pytest

import serve


@pytest.mark.parametrize("accept, coding", [
    ("", None), ("identity", None), ("gzip", "gzip"), ("br, gzip", "br"), ("gzip, br", "br"),
    ("br;q=0, gzip;q=1", "gzip"), ("br;q=0.5, gzip;q=0.8", "gzip"), ("*", "br"), ("*;q=0, identity", None),
    ("br;q=0, gzip;q=0", None),
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
