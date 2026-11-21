"""The draw against builder outputs (§2.1), and the control "An incidental
literal" of §2.5.5: a builder output holding a candidate fixture's amount in
its shortest JavaScript spelling makes the draw reject that amount, and the
accepted fixture's artifact, with the same literal, has no finding."""

from __future__ import annotations

import json

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
    shown = json.dumps(record["rejections"])  # classes, inspections and files — never a fixture value
    assert str(len(first.cells)) not in shown and not any(label in shown for label in f.CHANNELS)


def test_a_year_of_the_window_in_a_builder_output_moves_the_calendar(tmp_path, first):
    own = _builder(tmp_path, "own", f'export const label = "{first.year_month(0)}";\n')
    fx, record = cal.draw_against(SEED, {"own": own})
    assert fx.start != first.start
    assert any(r["class"] == "calendar" for r in record["rejections"])


# --- what the draw refuses to calibrate on, and its determinism (PROTO-1-07, -09) -------


def test_a_missing_builder_output_refuses_the_draw(tmp_path):
    import trees

    with pytest.raises(trees.Refused):
        cal.draw_against(SEED, {"own": tmp_path / "absent"})


def test_an_output_the_inspection_cannot_read_stops_the_draw(tmp_path):
    import os

    own = _builder(tmp_path, "own", "export const v = 1;\n")
    (own / "assets" / "blob.bin").write_bytes(os.urandom(512))
    with pytest.raises(f.DrawStopped) as raised:
        cal.draw_against(SEED, {"own": own})
    assert raised.value.reasons[0]["file"] == "own:assets/blob.bin"
    assert raised.value.record["draws"] == 1


def test_a_calendar_inside_a_compressed_structured_cell_moves_the_window(tmp_path, first):
    import gzip
    import io as io_mod

    import pyarrow as pa
    import pyarrow.ipc as ipc

    table = pa.table({"period": [f"period={first.year_month(2)}"]})
    sink = io_mod.BytesIO()
    with ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    own = _builder(tmp_path, "own", "export const v = 1;\n")
    (own / "assets" / "q.bin").write_bytes(gzip.compress(sink.getvalue()))
    fx, record = cal.draw_against(SEED, {"own": own})
    assert fx.start != first.start and any(r["class"] == "calendar" for r in record["rejections"])


def test_a_grouped_row_count_is_named_as_the_row_count(tmp_path, first):
    grouped = f"{len(first.cells):,}".replace(",", ".")
    own = _builder(tmp_path, "own", f'export const n = "{grouped}";\n')
    fx, record = cal.draw_against(SEED, {"own": own})
    assert "row_count" in {r["class"] for r in record["rejections"]} and fx.k != first.k


def test_the_draw_refuses_more_than_its_ceiling():
    with pytest.raises(ValueError):
        f.draw(SEED, lambda fx: [], limit=f.DRAWS_MAX + 1)


def test_a_seed_gives_one_fixture_whatever_the_hash_seed(tmp_path, first):
    import json
    import os
    import subprocess
    import sys

    amounts = [m.net for m in first.cells.values() if m.net.as_tuple().digits[-1] == 0][:2]
    own = _builder(tmp_path, "own", "".join(f"export const a{n} = {format(a.normalize(), 'f')};\n" for n, a in enumerate(amounts)))
    script = (f"import sys, json, hashlib; sys.path.insert(0, {str(f.HERE)!r}); import calibrate as cal, pathlib; "
              f"fx, rec = cal.draw_against({SEED}, {{'own': pathlib.Path({str(own)!r})}}); "
              "print(json.dumps([hashlib.sha256(repr(fx.rows()).encode()).hexdigest(), rec['rejections']]))")
    outs = {subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True,
                           env=os.environ | {"PYTHONHASHSEED": seed}).stdout for seed in ("1", "2")}
    assert len(outs) == 1
    assert json.loads(outs.pop())[1]


_REDRAW_SCRIPT = """
import builtins, hashlib, json, sys
sys.path.insert(0, {here!r})
import fixture as f
first = f.generate({seed})[0]
keys = sorted(first.cells)[:2]
a = f.Rejection("value", "carrier", "x.js", (keys[0],))
b = f.Rejection("value", "carrier", "y.js", (keys[1],))
if {mutate}:  # the draw with its sort of rejections removed, deduplication kept
    def unsorted(src, /, **kw):
        if isinstance(src, set) and src and all(isinstance(x, f.Rejection) for x in src):
            return list(src)
        return builtins.sorted(src, **kw)
    f.sorted = unsorted
def collides(fx):
    same = fx.cells[keys[0]] == first.cells[keys[0]] and fx.cells[keys[1]] == first.cells[keys[1]]
    return [a, b] if same else []
fx, _ = f.draw({seed}, collides)
print(hashlib.sha256(json.dumps(fx.rows(), default=str).encode()).hexdigest())
"""


def test_the_redraw_does_not_depend_on_the_order_rejections_come_in():
    """PROTO-2-11, PROTO-3-13: the same rejections give the same fixture under
    every hash seed — set order changes between processes, not within one —
    and the control is shown to fail with the draw's sort removed."""
    import os
    import subprocess
    import sys

    def digests(mutate: bool) -> set[str]:
        script = _REDRAW_SCRIPT.format(here=str(f.HERE), seed=SEED, mutate=mutate)
        return {subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True,
                               env=os.environ | {"PYTHONHASHSEED": str(h)}).stdout for h in range(1, 9)}

    assert len(digests(False)) == 1
    assert len(digests(True)) > 1, "the control cannot tell the sort from its absence"


def test_an_integral_arrow_float_equal_to_the_row_count_changes_k(tmp_path, first):
    """PROTO-2-08: a typed cell maps to its canonical source, not to a label."""
    import io as io_mod

    import pyarrow as pa
    import pyarrow.ipc as ipc

    table = pa.table({"n": [float(len(first.cells))]})
    sink = io_mod.BytesIO()
    with ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    own = _builder(tmp_path, "own", "export const v = 1;\n")
    (own / "assets" / "q.arrow").write_bytes(sink.getvalue())
    fx, record = cal.draw_against(SEED, {"own": own})
    assert fx.k != first.k and "row_count" in {r["class"] for r in record["rejections"]}
