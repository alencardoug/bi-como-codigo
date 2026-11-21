"""The controls of §2.5.5 that cross layers, on hand-made outputs: each has one
leak in one carrier, asserts its diagnosis at the layer it is for — the class
of `verify`, the carrier code of the inspection, the verdict — and the other
layers are recorded beside it."""

from __future__ import annotations

import hashlib
import json
import shutil

import pytest

import fixture as f
import harness as h
import inspect_output as io_
import verdict as v
from bi_como_codigo import contract as c, envelope as e

SEED = 20261120
LISTS = ("site/*\n", "".join(f"{x} application/octet-stream\n" for x in (".html", ".js", ".json", ".bice", ".map", ".txt", ".arrow")))


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
    assembly, validated = h.assemble(builder, pkg, fx.rows(), artifact)
    assert assembly.cls == h.PASS, assembly.message
    for rel, data in (artifact_extra or {}).items():
        (artifact / rel).parent.mkdir(parents=True, exist_ok=True)
        (artifact / rel).write_bytes(data)
    lists = tmp_path / "lists"
    lists.mkdir()
    (lists / "include.txt").write_text(LISTS[0])
    (lists / "media_types.txt").write_text(LISTS[1])
    result = h.verify(artifact, builder, h.write_root(tmp_path / "run", lists, decl), validated)
    needles = io_.Needles.from_fixture(fx)
    built = io_.inspect_dir(builder, needles)
    inspected = io_.inspect_dir(artifact, needles, validated={f"{k}": d for k, d in validated.files.items()})
    record = v.Record("r1", build_input="in", builder_digest="b", artifact_digest="a", stages={
        "build": v.Stage(), "archive": v.Stage(), "inspect_builder": v.Stage(findings=len(built.findings), inconclusive=len(built.inconclusive)),
        "assembly": v.Stage(cls=h.PASS), "verify": v.Stage(cls=result.cls),
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
