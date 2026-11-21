"""The draw against builder outputs (§2.1), and the control "An incidental
literal" of §2.5.5: a builder output holding a candidate fixture's amount in
its shortest JavaScript spelling makes the draw reject that amount, and the
accepted fixture's artifact, with the same literal, has no finding."""

from __future__ import annotations

import pytest

import calibrate as cal
import fixture as f
import harness as h
import inspect_output as io_

SEED = 20261120


def _builder(tmp_path, name, js: str):
    out = tmp_path / name
    (out / "assets").mkdir(parents=True)
    (out / "index.html").write_text("<!doctype html><title>P01</title><script type=module src=assets/app.js></script>")
    (out / "assets" / "app.js").write_text(js)
    return out


@pytest.fixture(scope="module")
def first():
    return f.generate(SEED)[0]


def test_an_incidental_literal_is_redrawn_and_the_accepted_artifact_is_clean(tmp_path, first):
    m = next(m for m in first.cells.values() if m.net.as_tuple().digits[-1] == 0 and m.net.as_tuple().digits[-2] != 0)
    literal = format(m.net.normalize(), "f")
    own = _builder(tmp_path, "own", f"export const ratio = {literal};\n")
    other = _builder(tmp_path, "evidence", "export const version = 1;\n")
    fx, record = cal.draw_against(SEED, {"own": own, "evidence": other})
    assert record["draws"] >= 2
    assert any(r["class"] == "value" and r["inspection"] == cal.CARRIER and r["file"] == "own:assets/app.js" for r in record["rejections"])
    assert m.net not in {x.net for x in fx.cells.values()}
    assert not cal.collision_search({"own": own, "evidence": other})(fx)

    totals, parquet = f.payload(fx)
    manifest, files = f.seal(totals, parquet)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (pkg / name).write_bytes(data)
    outcome, validated = h.assemble(own, pkg, fx.rows(), tmp_path / "artifact")
    assert outcome.cls == h.PASS
    lists = tmp_path / "lists"
    lists.mkdir()
    (lists / "include.txt").write_text("site/*\n")
    (lists / "media_types.txt").write_text(".html text/html\n.js text/javascript\n.json application/json\n.bice application/octet-stream\n")
    assert h.verify(tmp_path / "artifact", own, h.write_root(tmp_path / "run", lists), validated).cls == h.PASS
    report = io_.inspect_dir(tmp_path / "artifact", io_.Needles.from_fixture(fx), validated={k: v for k, v in validated.files.items()})
    assert report.clean, report.record()


def test_a_row_count_in_a_builder_output_changes_k(tmp_path, first):
    own = _builder(tmp_path, "own", f"export const n = {len(first.cells)};\n")
    fx, record = cal.draw_against(SEED, {"own": own})
    assert fx.k != first.k
    assert {r["class"] for r in record["rejections"]} >= {"row_count"}
    assert all("value" not in r for r in record["rejections"])


def test_a_year_of_the_window_in_a_builder_output_moves_the_calendar(tmp_path, first):
    own = _builder(tmp_path, "own", f'export const label = "{first.year_month(0)}";\n')
    fx, record = cal.draw_against(SEED, {"own": own})
    assert fx.start != first.start
    assert any(r["class"] == "calendar" for r in record["rejections"])
