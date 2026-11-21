"""The carrier inspection of §2.5.2, proved on hand-made carriers (§2.5.5, §7
step 1): each layer finds what it is for, with its code and decoding path,
roles keep small integers and code literals out, and what no layer reads is
inconclusive."""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import os
import struct
import urllib.parse
import zlib
from decimal import Decimal

import brotli
import pyarrow as pa
import pyarrow.ipc as ipc
import pytest
import zstandard

import fixture as f
import inspect_output as io_
from bi_como_codigo import contract as c, envelope as e, release

SEED = 20261120


@pytest.fixture(scope="module")
def fx():
    return f.generate(SEED)[0]


@pytest.fixture(scope="module")
def needles(fx):
    return io_.Needles.from_fixture(fx)


@pytest.fixture(scope="module")
def gate(fx):
    values = c.check_payload(f.contract(), f.contract().reports["P01"], *f.payload(fx))
    return values, c.needles([values], set())


@pytest.fixture(scope="module")
def samples(fx, gate):
    """One count, one amount whose fraction ends in 0 — its JavaScript spelling
    is shorter, and holds no needle of the gate — and one label."""
    m = next(m for m in fx.cells.values() if m.net.as_tuple().digits[-1] == 0 and m.net.as_tuple().digits[-2] != 0
             and not io_.gate_hits({"x": _js(m.net).encode()}, gate[1]))
    return {"count": next(iter(fx.cells.values())).order_count, "amount": m.net, "label": "fixture_canal_a"}


def _js(amount: Decimal) -> str:
    return format(amount.normalize(), "f")


def _rows_json(fx, n=3) -> bytes:
    return json.dumps([[str(v) if isinstance(v, Decimal) else v for v in r] for r in fx.rows()[:n]]).encode()


def _one(needles, name, data, **kw):
    return io_.inspect_items([io_.Item(name, data, **{k: v for k, v in kw.items() if k in {"role", "url"}})], needles,
                             **{k: v for k, v in kw.items() if k not in {"role", "url"}})


# --- clean, and what roles keep out ----------------------------------------------------


def test_a_clean_builder_output_has_no_finding(needles, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>P01</title><script type=module src=app.js></script>")
    (tmp_path / "app.js").write_text("export const version = 1; const months = [1,2,3,4,5,6,7,8,9,10,11,12];")
    report = io_.inspect_dir(tmp_path, needles)
    assert report.clean, report.record()


def test_clean_metadata_has_no_finding(needles):
    assert _one(needles, "meta.json", b'{"protocol_version": 1, "month": 4, "v": [1, 2]}').clean


def test_a_count_in_a_json_is_a_number(needles, samples):
    report = _one(needles, "data.json", json.dumps({"orders": samples["count"]}).encode())
    assert report.codes() == {io_.INSPECT_NUMBER}
    assert "data.json > json" in {x.path for x in report.findings}


def test_a_count_in_code_outside_a_structured_carrier_is_not_a_needle(needles, samples):
    assert _one(needles, "app.js", f"const x = {samples['count']};".encode()).clean


def test_a_count_in_a_data_bearing_carrier_is_found_in_any_spelling(needles, samples):
    n = samples["count"]
    for text in (f"orders={n}", f"{n:,}".replace(",", "."), f"{n:,}"):
        assert _one(needles, "store.txt", text.encode()).codes() == {io_.INSPECT_NUMBER}, text


def test_a_fixed_label_is_text(needles, samples):
    assert _one(needles, "label.txt", samples["label"].encode()).codes() == {io_.INSPECT_TEXT}


def test_an_amount_in_pt_br_is_text(needles, samples):
    spelled = c.spellings(str(samples["amount"]))[1]
    assert _one(needles, "a.html", f"<td>R$ {spelled}</td>".encode()).codes() == {io_.INSPECT_TEXT}


def test_an_amount_in_its_javascript_spelling_is_a_number_the_gate_misses(needles, samples, gate):
    js = _js(samples["amount"])
    assert len(js) < len(str(samples["amount"]))
    data = f"const v = [{js}, 2];".encode()
    assert _one(needles, "app.js", data).codes() == {io_.INSPECT_NUMBER}
    assert io_.gate_hits({"app.js": data}, gate[1]) == []


# --- structured, Arrow, Parquet ---------------------------------------------------------


def _arrow(fx, stream: bool) -> bytes:
    rows = fx.rows()[:3]
    table = pa.table({name: [r[i] for r in rows] for i, name in enumerate(f.COLUMNS)})
    sink = io.BytesIO()
    writer = (ipc.new_stream if stream else ipc.new_file)(sink, table.schema)
    writer.write_table(table)
    writer.close()
    return sink.getvalue()


@pytest.mark.parametrize("stream", [False, True])
def test_arrow_ipc_cells_are_compared_as_values(fx, needles, stream):
    report = _one(needles, "q.arrow", _arrow(fx, stream))
    assert report.codes() == {io_.INSPECT_ARROW}


def test_a_parquet_with_rows_is_found_and_one_with_none_is_schema_only(fx, needles):
    assert _one(needles, "p.parquet", f.parquet(fx.rows()[:2])).codes() == {io_.INSPECT_PARQUET}
    empty = _one(needles, "e.parquet", f.parquet([]))
    assert empty.clean and "schema only" in empty.recorded[0].reason


# --- decoders --------------------------------------------------------------------------


def _deflate_raw(data: bytes) -> bytes:
    co = zlib.compressobj(wbits=-15)
    return co.compress(data) + co.flush()


@pytest.mark.parametrize("name, wrap, step", [
    ("rows.bin", lambda d: gzip.compress(d), "gzip"),
    ("rows.bin", lambda d: zlib.compress(d), "zlib"),
    ("rows.bin", lambda d: brotli.compress(d), "brotli"),
    ("rows.bin", lambda d: zstandard.ZstdCompressor().compress(d), "zstd"),
    ("rows.bin", _deflate_raw, "deflate"),
    ("app.js", lambda d: b'const blob = "' + base64.b64encode(d) + b'";', "base64"),
    ("app.js", lambda d: b'const blob = "' + base64.urlsafe_b64encode(d).rstrip(b"=") + b'";', "base64"),
    ("app.js", lambda d: b'const blob = "' + d.hex().encode() + b'";', "hex"),
    ("a.html", lambda d: b'<a href="?q=' + urllib.parse.quote_from_bytes(d).encode() + b'">x</a>', "percent"),
    ("sw.js", lambda d: b"self.addEventListener('install', () => caches.put('" + base64.b64encode(gzip.compress(d)) + b"'));", "gzip"),
])
def test_each_decoder_reaches_the_rows(fx, needles, name, wrap, step):
    """Rows hidden under one encoding are found, with that step in the path."""
    report = _one(needles, name, wrap(_rows_json(fx)))
    assert report.findings, report.record()
    assert any(step in finding.path for finding in report.findings)


def test_json_escaped_text_and_html_entities_are_decoded(needles, samples):
    escaped = "".join(f"\\u{ord(ch):04x}" for ch in samples["label"])
    assert any("escapes" in x.path for x in _one(needles, "app.js", f'const s = "{escaped}";'.encode()).findings)
    entities = "".join(f"&#{ord(ch)};" for ch in samples["label"])
    assert any("entities" in x.path for x in _one(needles, "a.html", f"<p>{entities}</p>".encode()).findings)


def test_sveltekit_fetched_data_and_devalue_are_parsed(fx, needles, samples):
    body = base64.b64encode(json.dumps({"orders": samples["count"]}).encode()).decode()
    fetched = json.dumps({"status": 200, "statusText": "", "headers": {}, "body": body})
    page = (f'<script type="application/json" data-sveltekit-fetched data-url="/api/q" data-b64>{fetched}</script>'
            f'<script>{{__sveltekit_x = {{}}; const data = [null,{{type:"data",data:{{n:{samples["count"]}}}}}];}}</script>')
    report = _one(needles, "index.html", page.encode())
    paths = {x.path for x in report.findings if x.code == io_.INSPECT_NUMBER}
    assert any("script#0 > base64" in p for p in paths)
    assert any("script#1 > devalue" in p for p in paths)


def test_amounts_as_binary_doubles_and_decimal128_are_found(needles, samples):
    a = samples["amount"]
    for kind, raw in (("double-le", struct.pack("<d", float(a))), ("double-be", struct.pack(">d", float(a))),
                      ("decimal128", int(a * 100).to_bytes(16, "little"))):
        data = os.urandom(13) + raw + os.urandom(7)
        report = _one(needles, "x.bin", data, dependencies=frozenset({hashlib.sha256(data).hexdigest()}))
        assert any(x.code == io_.INSPECT_BINARY and kind in x.path for x in report.findings), kind


def test_too_many_layers_are_inconclusive(fx, needles):
    data = _rows_json(fx)
    for _ in range(io_.DEPTH + 1):
        data = gzip.compress(data)
    report = _one(needles, "deep.bin", data)
    assert report.inconclusive and "deeper" in report.inconclusive[0].reason


# --- what no layer reads, and what is recognised ---------------------------------------


def test_a_carrier_nobody_listed_is_inconclusive(fx, needles):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    sealed = AESGCM(AESGCM.generate_key(128)).encrypt(os.urandom(12), _rows_json(fx), None)
    report = _one(needles, "cache.bin", sealed)
    assert not report.findings and report.inconclusive and not report.clean


def test_a_binary_identical_to_a_dependency_file_is_recorded(needles):
    blob = os.urandom(4096)
    report = _one(needles, "engine.wasm", blob, dependencies=frozenset({hashlib.sha256(blob).hexdigest()}))
    assert report.clean and report.recorded


def test_a_pinned_body_is_recorded_and_a_changed_one_is_inconclusive(needles):
    body = b"export default 1;"
    url = "https://cdn.jsdelivr.net/npm/x@1.0.0/x.js"
    cdn = {url: hashlib.sha256(body).hexdigest()}
    assert _one(needles, "cdn", body, url=url, cdn=cdn).clean
    changed = _one(needles, "cdn", body + b"//", url=url, cdn=cdn)
    assert changed.inconclusive and not changed.findings


def _package(labels: list[str], fx):
    profiles = [e.DeclaredProfile("diretoria", label, "senha_complexa_123", ("P01",)) for label in labels]
    manifest, files = e.encrypt_package(profiles, {"P01": f.payload(fx)})
    digests = {"manifest.json": hashlib.sha256(manifest).hexdigest()} | {n: hashlib.sha256(d).hexdigest() for n, d in files.items()}
    items = [io_.Item("package/manifest.json", manifest)] + [io_.Item(f"package/{n}", d) for n, d in files.items()]
    return items, digests


def test_the_validated_package_is_recognised_and_its_labels_searched(fx, needles, samples):
    items, digests = _package(["Diretoria"], fx)
    report = io_.inspect_items(items, needles, validated=digests)
    assert report.clean and len(report.recorded) == 2
    items, digests = _package([f"Diretoria {_js(samples['amount'])}"], fx)
    labelled = io_.inspect_items(items, needles, validated=digests)
    assert labelled.codes() == {io_.INSPECT_NUMBER}
    assert labelled.findings[0].path == "manifest labels"


def test_a_package_file_with_another_digest_is_inspected_like_the_rest(fx, needles):
    items, digests = _package(["Diretoria"], fx)
    report = io_.inspect_items(items, needles, validated={})
    assert report.inconclusive  # an envelope not recognised is a binary no layer decodes


def test_a_collected_record_with_a_year_and_a_month_of_the_window_is_a_calendar_lead(fx, needles):
    y, m = fx.month(3)
    report = _one(needles, "history.state", json.dumps({"y": y, "m": m}).encode(), role=io_.COLLECTED)
    assert report.codes() == {io_.INSPECT_CALENDAR}
    assert _one(needles, "meta.json", json.dumps({"y": y, "m": m}).encode()).clean


def test_findings_are_recorded_without_their_values(needles, samples):
    report = _one(needles, "label.txt", samples["label"].encode())
    assert samples["label"] not in json.dumps(report.record())


# --- the gate's search, every hit ---------------------------------------------------------


def test_gate_hits_agrees_with_the_gates_inspect(gate):
    """Every sampled needle embedded in digits and punctuation is found by
    `gate_hits`, and by the gate's own `inspect` on a subset; a haystack with
    none, by neither."""
    values, needles = gate
    sample = needles[:: max(1, len(needles) // 300)]
    hays = {f"f{n}.js": b"x=1" + b"9.," + needle + b",.7;" for n, (_, needle) in enumerate(sample)}
    hits = {(code, needle, rel) for code, needle, rel in io_.gate_hits(hays, needles)}
    assert all((code, needle, f"f{n}.js") in hits for n, (code, needle) in enumerate(sample))
    for n in range(0, len(sample), len(sample) // 10):
        with pytest.raises(c.Refused):
            c.inspect({"a.js": hays[f"f{n}.js"]}, [values], set())
    clean = {"a.js": b"const a = 1, b = [2, 3, 4.5];"}
    c.inspect(clean, [values], set())
    assert io_.gate_hits(clean, needles) == []


# --- carriers the dispatch must not drop (PROTO-1-05) -----------------------------------


def test_a_label_in_base64_wrapped_brotli_inside_code_is_found(needles, samples):
    blob = base64.b64encode(brotli.compress(json.dumps({"c": samples["label"]}).encode())).decode()
    report = _one(needles, "app.js", f'const z = "{blob}";'.encode())
    assert any("brotli" in x.path for x in report.findings)


def test_every_zstd_frame_is_read(needles, samples):
    z = zstandard.ZstdCompressor()
    data = z.compress(b"nothing here") + z.compress(samples["label"].encode())
    assert _one(needles, "x.bin", data).codes() == {io_.INSPECT_TEXT}


def test_layers_beyond_the_depth_in_a_base64_file_are_never_clean(needles, samples):
    """Past the depth the bytes are still searched; a layer that would still
    open is inconclusive."""
    data = samples["label"].encode()
    for _ in range(io_.DEPTH + 1):
        data = base64.b64encode(data)
    assert _one(needles, "blob.txt", data).codes() == {io_.INSPECT_TEXT}
    data = base64.b64encode(gzip.compress(samples["label"].encode()))
    for _ in range(io_.DEPTH):
        data = base64.b64encode(data)
    deep = _one(needles, "deep.txt", data)
    assert not deep.clean and any("deeper" in x.reason for x in deep.inconclusive)


def test_a_data_b64_script_with_no_body_is_inconclusive(needles):
    page = '<script type="application/json" data-sveltekit-fetched data-b64>{"status": 200}</script>'
    assert _one(needles, "index.html", page.encode()).inconclusive


def test_a_legacy_arrow_stream_is_read(fx, needles):
    rows = fx.rows()[:2]
    table = pa.table({"order_count": [r[7] for r in rows]})
    sink = io.BytesIO()
    with ipc.new_stream(sink, table.schema, options=ipc.IpcWriteOptions(use_legacy_format=True)) as writer:
        writer.write_table(table)
    data = sink.getvalue()
    assert data[:4] != b"\xff\xff\xff\xff"
    assert io_.INSPECT_ARROW in _one(needles, "q.bin", data).codes()


def test_text_bytes_in_a_binary_are_found_before_a_dependency_exemption(needles, samples):
    blob = os.urandom(64) + samples["label"].encode() + os.urandom(64)
    report = _one(needles, "engine.wasm", blob, dependencies=frozenset({hashlib.sha256(blob).hexdigest()}))
    assert report.codes() == {io_.INSPECT_TEXT}


# --- numbers by role (PROTO-1-06) -----------------------------------------------------


def test_counts_in_exponent_narrow_space_grouping_and_amounts_before_a_comma_are_found(needles, samples):
    n = samples["count"]
    exponent = f"{Decimal(n).scaleb(-4).normalize()}e4"
    for text in (f"orders={exponent}", f"{n:,}".replace(",", " "), f"{n:,}".replace(",", " ")):
        assert io_.INSPECT_NUMBER in _one(needles, "store.txt", text.encode()).codes(), text
    spelled = c.spellings(str(samples["amount"]))[1]
    assert io_.INSPECT_TEXT in _one(needles, "a.html", f"<td>{spelled},7</td>".encode()).codes()


def test_a_negative_number_is_not_a_positive_needle(needles, samples):
    assert _one(needles, "store.txt", f"orders=-{samples['count']}".encode()).clean


def test_a_json_object_inside_code_is_a_structured_carrier(needles, samples):
    exponent = f"{Decimal(samples['count']).scaleb(-4).normalize()}e4"
    report = _one(needles, "app.js", f'const q = {{"orders": {exponent}}};'.encode())
    assert any("embedded json" in x.path and x.code == io_.INSPECT_NUMBER for x in report.findings)


def test_an_uppercase_json_script_is_parsed(needles, samples):
    page = f'<SCRIPT TYPE="APPLICATION/JSON">{{"n": {samples["count"]}}}</SCRIPT>'
    assert io_.INSPECT_NUMBER in _one(needles, "index.html", page.encode()).codes()


def test_the_manifest_labels_get_the_gates_full_search(fx, needles):
    year = str(fx.month(0)[0])
    items, digests = _package([f"Diretoria {year}"], fx)
    report = io_.inspect_items(items, needles, validated=digests)
    assert any(x.path == "manifest labels > the gate's needles" for x in report.findings)


def test_a_zero_row_parquet_with_other_types_is_not_schema_only(needles):
    import duckdb
    import tempfile

    cols = ", ".join(f'NULL::VARCHAR AS "{n}"' for n in f.COLUMNS)
    with tempfile.TemporaryDirectory() as d:
        duckdb.connect().execute(f"COPY (SELECT {cols} WHERE false) TO '{d}/x.parquet' (FORMAT parquet)")
        data = open(f"{d}/x.parquet", "rb").read()
    report = _one(needles, "wrong.parquet", data)
    assert not any("schema only" in x.reason for x in report.recorded)
