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


# --- round 2 (PROTO-2-05, -06, -08) ---------------------------------------------------


@pytest.mark.parametrize("inner", ["brotli", "legacy arrow"])
def test_a_layer_with_no_magic_past_the_depth_is_inconclusive(fx, needles, samples, inner):
    if inner == "brotli":
        data = brotli.compress(json.dumps({"c": samples["label"]}).encode())
    else:
        table = pa.table({"order_count": [samples["count"]]})
        sink = io.BytesIO()
        with ipc.new_stream(sink, table.schema, options=ipc.IpcWriteOptions(use_legacy_format=True)) as w:
            w.write_table(table)
        data = sink.getvalue()
    for _ in range(io_.DEPTH):
        data = base64.b64encode(data)
    report = _one(needles, "deep.txt", data)
    assert report.findings or any("deeper" in x.reason for x in report.inconclusive)


def test_a_truncated_final_zstd_frame_is_inconclusive(needles, samples):
    z = zstandard.ZstdCompressor()
    data = z.compress(b"nothing") + z.compress(samples["label"].encode() * 4)[:-1]
    report = _one(needles, "x.bin", data)
    assert any("ends before its end" in x.reason for x in report.inconclusive)


def test_a_count_in_a_hex_looking_string_of_a_data_carrier_is_found(needles, samples):
    import gzip as gz

    value = f"abcdef{samples['count']}abcdef0123"
    report = _one(needles, "rows.bin", gz.compress(json.dumps({"id": value}).encode()))
    assert io_.INSPECT_NUMBER in report.codes()


def test_a_scientific_literal_is_one_number(needles, samples):
    n = samples["count"]
    assert _one(needles, "store.txt", f"orders={n}e-1".encode()).clean
    assert _one(needles, "store.txt", f"orders=2e-{n}".encode()).clean
    assert io_.INSPECT_NUMBER in _one(needles, "store.txt", f"{n:,}".replace(",", " ").encode()).codes()
    assert _one(needles, "q.json", b'{"v": 1e309, "w": -1e309}').clean


def test_an_integral_arrow_float_names_its_canonical_count(fx, needles):
    table = pa.table({"c": [float(len(fx.cells))]})
    sink = io.BytesIO()
    with ipc.new_file(sink, table.schema) as w:
        w.write_table(table)
    report = _one(needles, "q.arrow", sink.getvalue())
    assert {x.value for x in report.findings} == {str(len(fx.cells))}


# --- round 3 (PROTO-3-05, PROTO-3-06) ------------------------------------------------


def test_a_label_split_across_two_zstd_frames_is_found(needles, samples):
    z = zstandard.ZstdCompressor()
    label = samples["label"].encode()
    data = z.compress(b'{"label":"' + label[:8]) + z.compress(label[8:] + b'"}')
    assert _one(needles, "x.bin", data).codes() == {io_.INSPECT_TEXT}


def test_a_split_label_in_a_truncated_stream_is_found_and_the_cut_reported(needles, samples):
    z = zstandard.ZstdCompressor()
    label = samples["label"].encode()
    data = z.compress(label[:8]) + z.compress(label[8:]) + z.compress(b"," * 200)[:-1]
    report = _one(needles, "x.bin", data)
    assert io_.INSPECT_TEXT in report.codes() and any("ends before its end" in x.reason for x in report.inconclusive)


def _nested_query(query: bytes) -> bytes:
    return base64.b64encode(base64.b64encode(gzip.compress(base64.b64encode(query), mtime=0)))


def test_a_percent_encoded_count_at_the_depth_limit_is_not_clean(fx, needles):
    count = len(fx.cells)
    query = urllib.parse.urlencode({"orders": f"{count:,}".replace(",", "\u202f")}).encode()
    assert io_.INSPECT_NUMBER in _one(needles, "query.txt", query).codes()
    report = _one(needles, "nested-export.txt", _nested_query(query))
    assert report.findings or any("deeper" in x.reason for x in report.inconclusive)


def test_ordinary_percent_text_at_the_depth_limit_stays_clean(needles):
    assert _one(needles, "nested-export.txt", _nested_query(b"lang=pt%2DBR&page=index")).clean


# --- round 3 (PROTO-3-07) -----------------------------------------------------------


def test_a_count_and_a_label_nested_in_arrow_and_parquet_cells_are_found(fx, needles, samples):
    import pyarrow.parquet as pq

    count = len(fx.cells)
    table = pa.table({"result": pa.array([{"orders": [count], "meta": {"tags": [samples["label"]]}}])})
    stream = io.BytesIO()
    with ipc.new_stream(stream, table.schema) as w:
        w.write_table(table)
    parquet = io.BytesIO()
    pq.write_table(table, parquet)
    for name, data, code in (("nested.arrow", stream.getvalue(), io_.INSPECT_ARROW), ("nested.parquet", parquet.getvalue(), io_.INSPECT_PARQUET)):
        report = _one(needles, name, data)
        assert report.codes() == {code}, name
        assert {str(x.value) for x in report.findings} == {str(count), samples["label"]}, name


# --- round 3 (PROTO-3-08) -----------------------------------------------------------


@pytest.fixture(scope="module")
def count_needles(needles):
    import dataclasses

    return dataclasses.replace(needles, counts=frozenset({20000}))


def test_a_count_before_an_adjacent_exponent_and_a_space_grouped_count_after_a_space_are_found(count_needles):
    for name, data in (("c.csv", b"20000,2e-1"), ("s.txt", b"orders = 20 000"), ("t.txt", b"total 20 000 pedidos")):
        assert io_.INSPECT_NUMBER in _one(count_needles, name, data, role="data").codes(), name


def test_a_scientific_literal_and_a_longer_grouping_are_not_partial_counts(count_needles):
    for data in (b"x 120 000", b"1 220 000", b"2e-1,3e4", b"120000,2e-1"):
        assert io_.INSPECT_NUMBER not in _one(count_needles, "n.txt", data, role="data").codes(), data


# --- round 4 (PROTO-4-05..08), the reviewer's cases ----------------------------------

_R4_LABEL = "fixture_cat_1_01"
_R4 = io_.Needles(frozenset({_R4_LABEL}), frozenset({Decimal("1234.50")}), frozenset({20000}), frozenset())


def _r4(name, data):
    return io_.inspect_items([io_.Item(name, data)], _R4)


def _wrap(data, layers):
    for _ in range(layers):
        data = base64.b64encode(data)
    return data


def test_skippable_zstd_frames_are_consumed():
    import struct as st

    z = zstandard.ZstdCompressor()
    skip = st.pack("<II", 0x184D2A50, 15) + b"stream metadata"
    one, two = z.compress(_R4_LABEL[:8].encode()), z.compress(_R4_LABEL[8:].encode())
    for data in (one + skip + two, skip + one + two):
        report = _r4("data.zst", data)
        assert report.codes() == {io_.INSPECT_TEXT} and not report.inconclusive


def test_embedded_json_at_the_depth_limit_is_not_clean_and_an_ordinary_path_is():
    holder = f'const cached = "{urllib.parse.quote(chr(123) + chr(34) + "n" + chr(34) + ":20000" + chr(125), safe="")}";\n'.encode()
    for layers in (3, 4):
        assert not _r4("app.js", _wrap(holder, layers)).clean, layers
    assert _r4("app.js", _wrap(urllib.parse.quote("folder/registration", safe="").encode(), 4)).clean
    assert _r4("app.js", _wrap(b"20% discount", 4)).clean


def _arrow_file(table):
    buf = io.BytesIO()
    with ipc.new_file(buf, table.schema, options=ipc.IpcWriteOptions(compression="zstd")) as w:
        w.write_table(table)
    return buf.getvalue()


def _parquet_file(table):
    import pyarrow.parquet as pq

    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    return buf.getvalue()


def test_a_count_only_in_an_arrow_dictionary_is_found():
    encoded = pa.array([20000, 42]).dictionary_encode()
    remaining = pa.table({"n": encoded.filter(pa.array([False, True]))})
    assert ipc.open_file(_arrow_file(remaining)).read_all().column(0).to_pylist() == [42]
    assert _r4("cache.arrow", _arrow_file(remaining)).codes() == {io_.INSPECT_ARROW}


@pytest.mark.parametrize("serialize", [_arrow_file, _parquet_file], ids=["arrow", "parquet"])
def test_a_textual_count_and_a_compressed_binary_cell_are_found(serialize):
    textual = pa.table({"m": pa.array([[("key", "Orders: 20000")]], type=pa.map_(pa.string(), pa.string()))})
    assert io_.INSPECT_NUMBER in _r4("cache.bin", serialize(textual)).codes()
    packed = gzip.compress(b'{"label":"' + _R4_LABEL.encode() + b'","filler":"' + b"x" * 200 + b'"}', mtime=0)
    assert _R4_LABEL.encode() not in packed
    assert io_.INSPECT_TEXT in _r4("cache.bin", serialize(pa.table({"d": [packed]}))).codes()


@pytest.mark.parametrize("text, found", [
    ("orders = .2e5", True), ("page 2 20 000", True), ("20000,2e-1", True), ("orders = 20 000", True),
    ("orders = 20000.e-5", False), ("orders = 1 020 000", False), ("orders = 1.020.000", False),
    ("orders = 1,020,000", False), ("1 220 000", False), ("120 000", False), ("5,20.000", True),
])
def test_numbers_are_read_as_whole_literals_and_groupings(text, found):
    assert (io_.INSPECT_NUMBER in _r4("results.txt", text.encode()).codes()) is found


# --- round 5 (PROTO-5-04..08), the reviewer's cases ----------------------------------

_R5_LABEL = "fixture_canal_a"
_R5 = io_.Needles(frozenset({_R5_LABEL}), frozenset({Decimal("1234.50")}), frozenset({20000}), frozenset())


def _r5(name, data):
    return io_.inspect_items([io_.Item(name, data)], _R5)


def _serialized(table, kind):
    import pyarrow.parquet as pq

    out = io.BytesIO()
    if kind == "parquet":
        pq.write_table(table, out, compression="zstd")
        return out.getvalue()
    opener = ipc.new_file if kind == "file" else ipc.new_stream
    with opener(out, table.schema, options=ipc.IpcWriteOptions(compression="zstd")) as w:
        w.write_table(table)
    return out.getvalue()


def _layouts():
    n, values = 20000, pa.array([42, 20000, 43])
    tensor_type = pa.fixed_shape_tensor(pa.int64(), [2])
    return {
        "large list view": (pa.LargeListViewArray.from_arrays([1], [1], values), ("file", "stream")),
        "list view": (pa.ListViewArray.from_arrays([1], [1], values), ("file",)),
        "run-end": (pa.RunEndEncodedArray.from_arrays(pa.array([2, 4], type=pa.int16()), pa.array([[n], [42]])), ("file",)),
        "tensor extension": (pa.ExtensionArray.from_storage(tensor_type, pa.array([[n, 42]], type=pa.list_(pa.int64(), 2))), ("file", "parquet")),
        "string view slice after the label": (pa.array([_R5_LABEL, "other long stored data"], type=pa.string_view()).slice(1, 1), ("file", "stream")),
        "binary view slice after a gzipped label": (
            pa.array([gzip.compress(_R5_LABEL.encode(), mtime=0), b"other long stored data"], type=pa.binary_view()).slice(1, 1), ("file",)),
        "escaped label in a JSON string": (pa.array(['{"data":"' + _R5_LABEL.replace("_", "\\u005f") + '"}']), ("file", "parquet")),
        "data URL in a string": (pa.array(["data:application/json;base64," + base64.b64encode(json.dumps({"l": _R5_LABEL}).encode()).decode()]),
                                 ("file", "parquet")),
    }


@pytest.mark.parametrize("name", sorted(_layouts()))
def test_stored_values_of_every_arrow_layout_are_found(name):
    array, kinds = _layouts()[name]
    for kind in kinds:
        assert not _r5(f"cache.{kind}", _serialized(pa.table({"c": array}), kind)).clean, (name, kind)


def test_a_run_end_slice_that_dropped_the_count_stays_clean():
    runs = pa.RunEndEncodedArray.from_arrays(pa.array([2, 4], type=pa.int16()), pa.array([[20000], [42]]))
    assert _r5("cache.file", _serialized(pa.table({"c": runs.slice(2, 1)}), "file")).clean


def test_a_parquet_dictionary_page_without_arrow_metadata_is_read_as_stored():
    import pyarrow.parquet as pq

    table = pa.table({"d": pa.array([_R5_LABEL, "other"]).dictionary_encode().filter(pa.array([False, True]))})
    out = io.BytesIO()
    pq.write_table(table, out, store_schema=False)
    assert pq.read_table(io.BytesIO(out.getvalue())).column("d").to_pylist() == ["other"]
    assert io_.INSPECT_PARQUET in _r5("cache.parquet", out.getvalue()).codes()


def test_opaque_bytes_in_a_binary_cell_are_inconclusive():
    report = _r5("cache.arrow", _serialized(pa.table({"d": [os.urandom(64)]}), "file"))
    assert any("binary cell" in x.path for x in report.inconclusive)


def test_a_gzipped_body_in_a_bundle_at_the_depth_limit_is_not_clean():
    worker = b"const r = " + json.dumps(base64.b64encode(gzip.compress(json.dumps({"l": _R5_LABEL}).encode(), mtime=0)).decode()).encode() + b";"
    assert io_.INSPECT_TEXT in _r5("worker.js", worker).codes()
    cell = _serialized(pa.table({"b": [base64.b64encode(worker)]}), "file")
    holder = b"const cache = " + json.dumps(base64.b64encode(gzip.compress(cell, mtime=0)).decode()).encode() + b";"
    assert not _r5("app.js", holder).clean


def test_compressed_metadata_and_a_cut_gzip_are_never_clean():
    import struct as st

    named = io.BytesIO()
    with gzip.GzipFile(filename=_R5_LABEL + ".json", mode="wb", fileobj=named, mtime=0) as g:
        g.write(b"clean body")
    assert io_.INSPECT_TEXT in _r5("app.js", base64.b64encode(named.getvalue())).codes()
    skip = st.pack("<II", 0x184D2A50, len(_R5_LABEL)) + _R5_LABEL.encode()
    assert io_.INSPECT_TEXT in _r5("data.zst", skip + zstandard.ZstdCompressor().compress(b"clean body")).codes()
    cut = gzip.compress(b'{"l": "' + _R5_LABEL.encode() + b'"}' + b" " * 200, mtime=0)[:-4]
    report = _r5("app.js", base64.b64encode(cut))
    assert any("ends before its end" in x.reason for x in report.inconclusive)


@pytest.mark.parametrize("name, text, found", [
    ("t.txt", "total = 20 000 123", False), ("t.txt", "total = 20 000.50", False), ("t.txt", "total = 20000.50", False),
    ("t.json", '{"total":20000.50}', False), ("t.txt", "total = 20 000", True), ("t.txt", "1.234,50,7", True),
    ("r.csv", "a,b,c\r\n20,000,123\r\n", False), ("r.csv", "a,b,c\r\n20,0,20000\r\n", True), ("r.csv", 'a,b\r\n5,"20,000"\r\n', True),
])
def test_rendered_numbers_keep_their_boundaries(name, text, found):
    codes = _r5(name, text.encode()).codes()
    if text == "1.234,50,7":
        assert io_.INSPECT_TEXT in codes or io_.INSPECT_NUMBER in codes  # the amount 1234.50 inside a longer run
    else:
        assert (io_.INSPECT_NUMBER in codes) is found, text


def test_a_spaced_amount_with_a_dot_decimal_is_found():
    assert not _r5("t.txt", b"amount = 1 234.50").clean


# --- the narrow adjustment of the Owner's N99 -------------------------------------------


def _fetched(body: dict) -> str:
    """A SvelteKit fetched-data script as Evidence's build writes it: a JSON
    whose `body` is itself a JSON, escaped into the string."""
    return ('<script type="application/json" data-sveltekit-fetched data-url="/api/q">'
            + json.dumps({"status": 200, "statusText": "", "headers": {}, "body": json.dumps(body)}) + "</script>")


def test_a_fetched_script_an_unescaping_breaks_is_recorded_not_inconclusive(needles, samples):
    """Read as it is on the page; the layer of `escapes` turns its `\\"` into
    `"` and breaks it, which is no carrier left unread (N99)."""
    report = _one(needles, "index.html", f"<p>a\\nb</p>{_fetched({'customFormats': []})}".encode())
    assert report.clean, report.record()
    assert any("unescaping broke" in x.reason and "escapes" in x.path for x in report.recorded)
    found = _one(needles, "index.html", _fetched({"orders": samples["count"]}).encode())
    assert any(x.code == io_.INSPECT_NUMBER and "script#0 > json" in x.path for x in found.findings)


def test_a_broken_script_on_an_unescaped_layer_is_searched_as_data(needles, samples):
    """A count in a JSON script that only an unescaping reveals, and that does
    not parse there, is still found: searched with every integer needle, as a
    data-bearing carrier, though the page itself is code (N99)."""
    page = f'<p>&lt;script type="application/json"&gt;{{"orders": {samples["count"]}, broken&lt;/script&gt;</p>'
    report = _one(needles, "index.html", page.encode())
    assert any(x.code == io_.INSPECT_NUMBER and x.path.endswith("entities > script#0 > as data") for x in report.findings)


def test_a_decoding_that_changes_nothing_is_no_layer(needles):
    """`&t;` looks like an entity and decodes to itself: the bundle is not
    read again, layer after layer, past the depth (N99)."""
    bundle = b'const map = {"a": [1, 2]}; const amp = "&t;";'
    report = _one(needles, "app.js", bundle)
    assert report.clean and not report.inconclusive, report.record()
    assert not any("entities" in x.path for x in report.inconclusive + report.recorded)

