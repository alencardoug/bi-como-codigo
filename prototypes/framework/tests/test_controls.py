"""The controls of §2.5.5 that cross layers, on hand-made outputs: each has one
leak in one carrier, asserts its diagnosis at the layer it is for — the class
of `verify`, the carrier code of the inspection, the verdict — and the other
layers are recorded beside it."""

from __future__ import annotations

import hashlib
import json
import shutil
from decimal import Decimal

import pytest

import fixture as f
import harness as h
import inspect_output as io_
import verdict as v
from bi_como_codigo import contract as c, envelope as e

SEED = 20261120
LISTS = ("site/*\n", "".join(f"{x} application/octet-stream\n" for x in (".html", ".js", ".json", ".bice", ".map", ".txt", ".arrow", ".bin")))


@pytest.fixture(scope="module")
def fx():
    return f.generate(SEED)[0]


def _package(tmp_path, fx, label="Diretoria"):
    profiles = [e.DeclaredProfile("diretoria", label, "senha_complexa_123", ("P01",))]
    manifest, files = e.encrypt_package(profiles, {"P01": f.payload(fx)})
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (pkg / name).write_bytes(data)
    return pkg


def _all_layers(tmp_path, fx, *, builder_extra=None, artifact_extra=None, label="Diretoria", relabel_declarations=False):
    builder = tmp_path / "builder"
    (builder / "assets").mkdir(parents=True)
    (builder / "index.html").write_text("<!doctype html><title>P01</title>")
    for rel, data in (builder_extra or {}).items():
        (builder / rel).parent.mkdir(parents=True, exist_ok=True)
        (builder / rel).write_bytes(data)
    decl = h.DECLARATIONS
    if relabel_declarations:  # the package's label is the declared one, so that assembly validates it
        decl = tmp_path / "decl"
        shutil.copytree(h.DECLARATIONS, decl)
        data = json.loads((decl / "profiles.json").read_text())
        data["profiles"][0]["label"] = label
        (decl / "profiles.json").write_text(json.dumps(data))
    pkg = _package(tmp_path, fx, label)
    artifact = tmp_path / "artifact"
    assembly, validated = h.assemble(builder, pkg, fx.rows(), artifact, control_additions=artifact_extra)
    assert assembly.cls == h.PASS, assembly.message
    lists = tmp_path / "lists"
    lists.mkdir()
    (lists / "include.txt").write_text(LISTS[0])
    (lists / "media_types.txt").write_text(LISTS[1])
    result = h.verify(artifact, builder, h.write_root(tmp_path / "run", lists, decl), validated,
                      label="control" if artifact_extra else "judged")
    needles = io_.Needles.from_fixture(fx)
    built = io_.inspect_dir(builder, needles)
    inspected = io_.inspect_dir(artifact, needles, validated={f"{k}": d for k, d in validated.files.items()})
    record = v.Record("r1", build_input="in", builder_digest="b", artifact_digest="a", stages={
        "build": v.Stage(), "archive": v.Stage(), "inspect_builder": v.Stage(findings=len(built.findings), inconclusive=len(built.inconclusive)),
        "assembly": v.Stage(cls=assembly.cls), "verify": v.Stage(cls=result.cls),
        "inspect_artifact": v.Stage(findings=len(inspected.findings), inconclusive=len(inspected.inconclusive))})
    return result, inspected, v.verdict([record])


def _js(amount):
    return format(amount.normalize(), "f")


def _ending_in_zero(fx):
    """An amount whose JavaScript spelling is shorter and holds no needle of the gate."""
    values = c.check_payload(f.contract(), f.contract().reports["P01"], *f.payload(fx))
    gate = c.needles([values], set())
    return next(m.net for m in fx.cells.values() if m.net.as_tuple().digits[-1] == 0 and m.net.as_tuple().digits[-2] != 0
                and not io_.gate_hits({"x": _js(m.net).encode()}, gate))


def test_package_only_with_a_form_refusal(tmp_path, fx):
    result, inspected, verdict = _all_layers(tmp_path, fx, artifact_extra={"assets/manifest.json": b"{}"})
    assert result.cls == h.FORM
    assert inspected.clean, inspected.record()  # the package's files are recognised by digest
    assert verdict.name == v.COST


def test_a_numeric_label_behind_form_fails(tmp_path, fx):
    label = f"Diretoria {_js(_ending_in_zero(fx))}"
    result, inspected, verdict = _all_layers(tmp_path, fx, artifact_extra={"assets/manifest.json": b"{}"}, label=label, relabel_declarations=True)
    assert result.cls == h.FORM
    assert {x.code for x in inspected.findings if x.file == "package/manifest.json"} == {io_.INSPECT_NUMBER}
    assert verdict.name == v.FAILS


def test_content_behind_form_fails(tmp_path, fx):
    result, inspected, verdict = _all_layers(tmp_path, fx, artifact_extra={"assets/app.js.map": b'{"sources": ["fixture_canal_a"]}'})
    assert result.cls == h.FORM
    assert io_.INSPECT_TEXT in inspected.codes()
    assert verdict.name == v.FAILS


def test_a_fixed_label_is_content_and_text(tmp_path, fx):
    result, inspected, verdict = _all_layers(tmp_path, fx, artifact_extra={"assets/label.txt": b"fixture_raiz_3"})
    assert (result.cls, inspected.codes(), verdict.name) == (h.CONTENT, {io_.INSPECT_TEXT}, v.FAILS)


@pytest.mark.parametrize("carrier, verify_cls, code", [
    ("pt-BR", h.CONTENT, io_.INSPECT_TEXT),
    ("javascript", h.PASS, io_.INSPECT_NUMBER),
])
def test_a_varying_value_in_one_carrier(tmp_path, fx, carrier, verify_cls, code):
    amount = _ending_in_zero(fx)
    text = c.spellings(str(amount))[1] if carrier == "pt-BR" else f"const v = {_js(amount)};"
    result, inspected, verdict = _all_layers(tmp_path, fx, artifact_extra={"assets/v.js": text.encode()})
    assert result.cls == verify_cls
    assert code in inspected.codes()
    assert verdict.name == v.FAILS


# --- the varying carriers, the second manifest, the opaque carrier (PROTO-1-13) ---------


def _rows_json(fx, n=3) -> bytes:
    return json.dumps([[str(x) if isinstance(x, Decimal) else x for x in r] for r in fx.rows()[:n]]).encode()


def _arrow_counts(fx) -> bytes:
    import io

    import pyarrow as pa
    import pyarrow.ipc as ipc

    table = pa.table({"order_count": [r[7] for r in fx.rows()[:3]]})  # numbers only: no label for the gate to see
    sink = io.BytesIO()
    with ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.getvalue()


def _carriers(fx):
    import base64
    import gzip

    import brotli

    rows = _rows_json(fx)
    escaped = "".join(f"\\u{ord(ch):04x}" for ch in "fixture_canal_a")
    return {
        "arrow": ("assets/q.arrow", _arrow_counts(fx), io_.INSPECT_ARROW),
        "gzip": ("assets/rows.bin", gzip.compress(rows), io_.INSPECT_TEXT),
        "brotli": ("assets/rows2.bin", brotli.compress(rows), io_.INSPECT_TEXT),
        "base64": ("assets/rows.txt", base64.b64encode(rows), io_.INSPECT_TEXT),
        "escaped": ("assets/s.js", f'const s = "{escaped}";'.encode(), io_.INSPECT_TEXT),
        "service worker": ("sw.js", b"self.data = '" + base64.b64encode(gzip.compress(rows)) + b"';", io_.INSPECT_TEXT),
    }


@pytest.mark.parametrize("carrier", ["arrow", "gzip", "brotli", "base64", "escaped", "service worker"])
def test_a_varying_value_the_gate_cannot_see_is_found_by_the_inspection(tmp_path, fx, carrier):
    rel, data, code = _carriers(fx)[carrier]
    result, inspected, verdict = _all_layers(tmp_path, fx, artifact_extra={rel: data})
    assert result.cls == h.PASS, result.message
    assert code in inspected.codes() and any(x.file == rel for x in inspected.findings)
    assert verdict.name == v.FAILS


def test_a_label_in_a_second_manifest_of_the_builder_is_behind_form_and_fails(tmp_path, fx):
    result, inspected, verdict = _all_layers(tmp_path, fx, builder_extra={"assets/manifest.json": b'{"name": "fixture_canal_a"}'})
    assert result.cls == h.FORM and result.message.startswith("2 package manifests")
    assert any(x.file == "assets/manifest.json" and x.code == io_.INSPECT_TEXT for x in inspected.findings)
    assert verdict.name == v.FAILS


def test_a_carrier_nobody_listed_is_not_established_even_after_a_clean_run_of_another_artifact(tmp_path, fx):
    import os

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    sealed = AESGCM(AESGCM.generate_key(128)).encrypt(os.urandom(12), _rows_json(fx), None)
    result, inspected, verdict = _all_layers(tmp_path / "a", fx, artifact_extra={"assets/cache.bin": sealed})
    assert result.cls == h.PASS and not inspected.findings and inspected.inconclusive
    assert verdict.name == v.NOT_ESTABLISHED
    _, clean, _ = _all_layers(tmp_path / "b", fx)
    assert clean.clean
    history = [
        v.Record("r1", build_input="in", builder_digest="b", artifact_digest="a1", stages={
            "build": v.Stage(), "archive": v.Stage(), "inspect_builder": v.Stage(), "assembly": v.Stage(cls=h.PASS),
            "verify": v.Stage(cls=result.cls), "inspect_artifact": v.Stage(inconclusive=len(inspected.inconclusive))}),
        v.Record("r2", build_input="in2", builder_digest="b2", artifact_digest="a2", stages={
            "build": v.Stage(), "archive": v.Stage(), "inspect_builder": v.Stage(), "assembly": v.Stage(cls=h.PASS),
            "verify": v.Stage(cls=h.PASS), "inspect_artifact": v.Stage(inconclusive=len(clean.inconclusive))}),
    ]
    assert v.verdict(history).name == v.NOT_ESTABLISHED


# --- each control fails without the detection it exercises ------------------------------


@pytest.mark.parametrize("carrier, detector", [
    ("gzip", "_decompress_by_magic"),
    ("arrow", "_arrow"),
    ("escaped", "_text_decoders"),
])
def test_removing_the_detection_makes_its_control_fail(tmp_path, fx, monkeypatch, carrier, detector):
    rel, data, code = _carriers(fx)[carrier]
    monkeypatch.setattr(io_, detector, {"_decompress_by_magic": lambda d: None, "_arrow": lambda *a: False,
                                        "_text_decoders": lambda text: iter(())}[detector])
    _, inspected, verdict = _all_layers(tmp_path, fx, artifact_extra={rel: data})
    assert not any(x.file == rel and x.code == code for x in inspected.findings)
