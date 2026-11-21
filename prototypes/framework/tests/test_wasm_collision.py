"""The control "Collision" of §2.5.5, on DuckDB-WASM 1.32.0's real EH WASM: a
forced fixture whose row count round 3 measured in that file is a COLLISION,
established by reproduction, with the row count's class named; the same with
the reproduction given another haystack role is the harness's; and the
fixture of §2.1, drawn against that output with a short limit, ends as the
draw exhausted — never as a failure of a candidate.

The tarball is fetched once by the fetcher into `runs/third_party/`, checked
against the registry's integrity:

    make prototype-third-party
"""

from __future__ import annotations

import hashlib
import pathlib
import tarfile

import pytest

import calibrate as cal
import fixture as f
import harness as h

TARBALL = f.HERE / "runs" / "third_party" / "duckdb-wasm-1.32.0.tgz"
pytestmark = pytest.mark.skipif(not TARBALL.exists(), reason="run `make prototype-third-party` first")


@pytest.fixture(scope="module")
def builder(tmp_path_factory):
    out = tmp_path_factory.mktemp("builder")
    (out / "assets").mkdir()
    (out / "index.html").write_text("<!doctype html><title>P01</title>")
    with tarfile.open(TARBALL) as t:
        (out / "assets" / "duckdb-eh.wasm").write_bytes(t.extractfile("package/dist/duckdb-eh.wasm").read())
    return out


def _forced_package(tmp_path, rows):
    manifest, files = f.seal(f.totals(rows), f.parquet(rows))
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (pkg / name).write_bytes(data)
    return pkg


@pytest.mark.parametrize("role, expected", [(None, h.COLLISION), ("labels", h.HARNESS_ERROR)])
def test_a_row_count_measured_in_the_engine_is_a_collision(tmp_path, builder, role, expected):
    fx, _ = f.generate(20261120)
    rows = fx.rows()[:220]
    assert b"220" in (builder / "assets" / "duckdb-eh.wasm").read_bytes()
    outcome, validated = h.assemble(builder, _forced_package(tmp_path, rows), rows, tmp_path / "artifact")
    assert outcome.cls == h.PASS
    lists = tmp_path / "lists"
    lists.mkdir()
    (lists / "include.txt").write_text("site/*\n")
    (lists / "media_types.txt").write_text(".html text/html\n.wasm application/wasm\n.json application/json\n.bice application/octet-stream\n")
    result = h.verify(tmp_path / "artifact", builder, h.write_root(tmp_path / "run", lists), validated, role_override=role,
                      label="control" if role else "judged")
    assert result.cls == expected, result.message
    if expected == h.COLLISION:
        assert result.detail["file"] == "assets/duckdb-eh.wasm"
        assert "row_count" in result.detail["classes"]


def test_a_draw_with_no_clean_fixture_against_that_output_is_exhausted(builder):
    with pytest.raises(f.DrawExhausted) as raised:
        wasm = hashlib.sha256((builder / "assets" / "duckdb-eh.wasm").read_bytes()).hexdigest()
        cal.draw_against(20261120, {"engine": builder}, limit=2, dependencies={"engine": frozenset({wasm})})
    record = raised.value.record
    assert record["draws"] == 2 and record["rejections"]
    assert {r["file"] for r in record["rejections"]} <= {"engine:assets/duckdb-eh.wasm", "engine:index.html"}
