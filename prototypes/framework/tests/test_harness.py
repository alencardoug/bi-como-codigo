"""Assembly, `verify` under the harness's root, and the class of each outcome
(docs/framework_prototype.md §2.2, §2.5.1): every row of §2.5.1's table proved
by its own control, on hand-made builder outputs (§7 step 1)."""

from __future__ import annotations

import json
import os
import pathlib
import shutil

import pytest

import fixture as f
import harness as h
import trees
from bi_como_codigo import contract as c, envelope as e, release

SEED = 20261120
INCLUDE_ALL = "site/*\n"
MEDIA_ALL = "".join(f"{ext} application/octet-stream\n" for ext in (".html", ".js", ".json", ".bice", ".parquet", ".map", ".txt", ".bin"))


@pytest.fixture(scope="module")
def sealed(tmp_path_factory):
    fx, _ = f.generate(SEED)
    totals, parquet = f.payload(fx)
    manifest, files = f.seal(totals, parquet)
    pkg = tmp_path_factory.mktemp("pkg") / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (pkg / name).write_bytes(data)
    return fx, pkg, totals, parquet


def _builder(base: pathlib.Path, extra: dict[str, bytes] | None = None) -> pathlib.Path:
    out = base / "builder"
    (out / "assets").mkdir(parents=True)
    (out / "index.html").write_bytes(b"<!doctype html><title>P01</title><script type=module src=assets/app.js></script>")
    (out / "assets" / "app.js").write_bytes(b"export const version = 1;\n")
    for rel, data in (extra or {}).items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(data)
    return out


def _lists(base: pathlib.Path, include: str = INCLUDE_ALL, media: str = MEDIA_ALL) -> pathlib.Path:
    lists = base / "lists"
    lists.mkdir()
    (lists / "include.txt").write_text(include)
    (lists / "media_types.txt").write_text(media)
    return lists


def _run(tmp_path, sealed, *, builder_extra=None, artifact_extra=None, include=INCLUDE_ALL, media=MEDIA_ALL,
         expected=None, role_override=None, declarations=h.DECLARATIONS, after_assembly=None, builder_hook=None):
    """Assembly and `verify`. `artifact_extra` are a control's additions,
    declared to assembly; `after_assembly` changes the artifact afterwards, which
    the bound `verify` must refuse as the harness's — the row of §2.5.1's table
    is then read through `run_gate`, unbound (PROTO-1-02)."""
    fx, pkg, _, _ = sealed
    builder = _builder(tmp_path, builder_extra)
    if builder_hook:
        builder_hook(builder)
    artifact = tmp_path / "artifact"
    outcome, validated = h.assemble(builder, pkg, expected if expected is not None else fx.rows(), artifact,
                                    control_additions=artifact_extra)
    if outcome.cls != h.PASS:
        return outcome
    if after_assembly:
        after_assembly(artifact)
    root = h.write_root(tmp_path / "run", _lists(tmp_path, include, media), declarations)
    if after_assembly:
        bound = h.verify(artifact, builder, root, validated, role_override=role_override, label="control")
        assert (bound.cls, bound.message) == (h.HARNESS_ERROR, "the artifact is not the one assembled with the validated package")
        return h.run_gate(artifact, builder, root, validated, role_override=role_override, table_control=True)
    label = "control" if artifact_extra or role_override else "judged"
    return h.verify(artifact, builder, root, validated, role_override=role_override, label=label)


# --- the clean control and assembly --------------------------------------------------


def test_the_clean_artifact_passes(tmp_path, sealed):
    outcome = _run(tmp_path, sealed)
    assert (outcome.stage, outcome.cls) == ("verify", h.PASS)


def test_the_artifact_is_the_builder_output_plus_the_validated_package(tmp_path, sealed):
    fx, pkg, _, _ = sealed
    builder = _builder(tmp_path)
    outcome, validated = h.assemble(builder, pkg, fx.rows(), tmp_path / "artifact")
    assert outcome.cls == h.PASS
    assert set(validated.files) == {p.name for p in pkg.iterdir()}
    assert sorted(p.name for p in (tmp_path / "artifact" / "package").iterdir()) == sorted(validated.files)


def test_a_builder_output_with_its_own_package_is_form_at_assembly(tmp_path, sealed):
    outcome = _run(tmp_path, sealed, builder_extra={"package/manifest.json": b"{}"})
    assert (outcome.stage, outcome.cls) == ("assembly", h.FORM)


def test_a_corrupted_envelope_is_the_harnesss_at_assembly(tmp_path, sealed):
    fx, pkg, _, _ = sealed
    broken = tmp_path / "broken"
    shutil.copytree(pkg, broken)
    env = next(p for p in broken.iterdir() if p.suffix == ".bice")
    data = bytearray(env.read_bytes())
    data[-1] ^= 1
    env.write_bytes(bytes(data))
    outcome, _ = h.assemble(_builder(tmp_path), broken, fx.rows(), tmp_path / "artifact")
    assert (outcome.stage, outcome.cls) == ("assembly", h.HARNESS_ERROR)


def test_a_package_of_another_fixture_is_the_harnesss_at_assembly(tmp_path, sealed):
    other, _ = f.generate(SEED + 1)
    outcome = _run(tmp_path, sealed, expected=other.rows())
    assert (outcome.stage, outcome.cls) == ("assembly", h.HARNESS_ERROR)
    assert "expected rows" in outcome.message


# --- verify: the declarations and the package are the harness's ----------------------


def _declarations(tmp_path, **changes):
    out = tmp_path / "decl"
    shutil.copytree(h.DECLARATIONS, out)
    for name, data in changes.items():
        if data is None:
            (out / name).unlink()
        else:
            (out / name).write_text(data)
    return out


@pytest.mark.parametrize("changes", [
    {"contract.json": None},
    {"public_values.json": '{"about": "x"}'},
    {"profiles.json": None},
])
def test_a_broken_declaration_is_the_harnesss(tmp_path, sealed, changes):
    outcome = _run(tmp_path, sealed, declarations=_declarations(tmp_path, **{k.replace("_json", ".json"): v for k, v in changes.items()}))
    assert (outcome.stage, outcome.cls) == ("verify", h.HARNESS_ERROR)


def test_a_malformed_inclusion_list_is_the_harnesss(tmp_path, sealed):
    outcome = _run(tmp_path, sealed, include="assets/*\n")
    assert outcome.cls == h.HARNESS_ERROR and "is not a path under site/" in outcome.message


def test_a_malformed_media_types_list_is_the_harnesss(tmp_path, sealed):
    outcome = _run(tmp_path, sealed, media=".html\n")
    assert outcome.cls == h.HARNESS_ERROR


def test_the_package_not_placed_is_the_harnesss(tmp_path, sealed):
    outcome = _run(tmp_path, sealed, after_assembly=lambda a: shutil.rmtree(a / "package"))
    assert outcome.cls == h.HARNESS_ERROR and outcome.message.startswith("0 package manifests")


@pytest.mark.parametrize("damage, message", [
    ("manifest", "package manifest refused"),
    ("missing_envelope", "is in the manifest and not in the artifact"),
    ("stray_envelope", "envelopes not in the manifest"),
])
def test_a_package_changed_after_assembly_is_the_harnesss(tmp_path, sealed, damage, message):
    def change(artifact):
        pkg = artifact / "package"
        env = next(p for p in pkg.iterdir() if p.suffix == ".bice")
        if damage == "manifest":
            (pkg / "manifest.json").write_bytes(b"{}")
        elif damage == "missing_envelope":
            env.unlink()
        else:
            shutil.copyfile(env, pkg / "P01.0000000000000000.bice")

    outcome = _run(tmp_path, sealed, after_assembly=change)
    assert outcome.cls == h.HARNESS_ERROR and message in outcome.message


def _replace_package(artifact, profiles, totals, parquet):
    manifest, files = e.encrypt_package(profiles, {"P01": (totals, parquet)})
    shutil.rmtree(artifact / "package")
    (artifact / "package").mkdir()
    (artifact / "package" / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (artifact / "package" / name).write_bytes(data)


def test_a_package_under_other_entitlements_is_the_harnesss(tmp_path, sealed):
    _, _, totals, parquet = sealed
    profiles = release.profiles(f.HERE) + [e.DeclaredProfile("outro", "Outro", "senha_complexa_123", ("P01",))]
    outcome = _run(tmp_path, sealed, after_assembly=lambda a: _replace_package(a, profiles, totals, parquet))
    assert outcome.cls == h.HARNESS_ERROR and outcome.message.startswith("entitlements_exact")


def test_a_package_with_wrong_totals_is_the_harnesss(tmp_path, sealed):
    fx, _, totals, parquet = sealed
    wrong = json.loads(totals)
    wrong["rows"] += 1
    raw = json.dumps(wrong, separators=(",", ":")).encode()
    outcome = _run(tmp_path, sealed, after_assembly=lambda a: _replace_package(a, release.profiles(f.HERE), raw, parquet))
    assert outcome.cls == h.HARNESS_ERROR and outcome.message.startswith("totals_rows")


def test_an_unlisted_refusal_or_an_exception_is_the_harnesss(tmp_path, sealed, monkeypatch):
    def refuse(*args, **kwargs):
        raise release.Refused("a message no row of the table lists")

    monkeypatch.setattr(release, "verify", refuse)
    assert _run(tmp_path, sealed).cls == h.HARNESS_ERROR

    def explode(*args, **kwargs):
        raise KeyError("x")

    monkeypatch.setattr(release, "verify", explode)
    assert _run(tmp_path / "b", sealed).cls == h.HARNESS_ERROR


# --- verify: the candidate's form --------------------------------------------------


def _symlink(builder):
    os.symlink("index.html", builder / "link.html")


def _fifo(builder):
    os.mkfifo(builder / "pipe.txt")


@pytest.mark.parametrize("kwargs, message", [
    ({"builder_extra": {"assets/manifest.json": b"{}"}}, "2 package manifests"),
    ({"builder_extra": {"assets/extra.js": b"1"}, "include": "site/index.html\nsite/assets/app.js\nsite/package/*\n"}, "is not under the inclusion list"),
    ({"builder_extra": {"assets/font.woff2": b"1"}}, "extension not in media_types.txt"),
    ({"builder_extra": {"assets/app.js.map": b"{}"}}, "is a source map"),
    ({"builder_extra": {"assets/b.js": b"//# sourceMappingURL=b.js.map"}}, "references a source map"),
    ({"builder_extra": {"__/firebase/init.json": b"{}"}}, "reserved __/ URLs"),
    ({"builder_hook": _symlink}, "is a symbolic link"),
    ({"builder_hook": _fifo}, "is not a plain file"),
    ({"builder_extra": {"assets/schema_exact.js": b"1"}, "media": ".html text/html\n.json application/json\n.bice application/octet-stream\n"},
     "extension not in media_types.txt"),
])
def test_each_form_refusal_is_form(tmp_path, sealed, kwargs, message):
    outcome = _run(tmp_path, sealed, **kwargs)
    assert outcome.cls == h.FORM and message in outcome.message


# --- verify: content, schema only, and collisions --------------------------------------


def _parquet_with(rows):
    return f.parquet(rows)


def test_a_zero_row_parquet_of_p01s_schema_is_schema_only(tmp_path, sealed):
    outcome = _run(tmp_path, sealed, builder_extra={"assets/empty.parquet": _parquet_with([])})
    assert outcome.cls == h.SCHEMA_ONLY


def test_a_parquet_with_one_fixture_row_is_content(tmp_path, sealed):
    fx = sealed[0]
    outcome = _run(tmp_path, sealed, builder_extra={"assets/one.parquet": _parquet_with(fx.rows()[:1])})
    assert outcome.cls == h.CONTENT


def test_a_clear_payload_and_a_data_key_are_content(tmp_path, sealed):
    _, pkg, totals, parquet = sealed
    assert _run(tmp_path, sealed, artifact_extra={"assets/p.bin": e.build_payload(b"{}", b"PAR1xxxxPAR1")[:8]}).cls == h.CONTENT
    manifest_raw = (pkg / "manifest.json").read_bytes()
    envelopes = {p.name: p.read_bytes() for p in pkg.iterdir() if p.suffix == ".bice"}
    dek = release._deks(e.validate_manifest(manifest_raw), envelopes, {"diretoria": "senha_complexa_123"})[0]
    outcome = _run(tmp_path / "k", sealed, artifact_extra={"assets/k.txt": dek.hex().encode()})
    assert outcome.cls == h.CONTENT and "data key" in outcome.message


def test_a_fixture_label_added_to_the_artifact_is_content(tmp_path, sealed):
    outcome = _run(tmp_path, sealed, artifact_extra={"assets/label.txt": b"fixture_canal_a"})
    assert outcome.cls == h.CONTENT and outcome.detail["file"] == "assets/label.txt"


def test_an_amount_in_pt_br_added_to_the_artifact_is_content(tmp_path, sealed):
    fx = sealed[0]
    amount = str(next(iter(fx.cells.values())).net)
    outcome = _run(tmp_path, sealed, artifact_extra={"assets/amount.txt": c.spellings(amount)[1].encode()})
    assert outcome.cls == h.CONTENT


def test_a_needle_already_in_the_builder_output_is_a_collision(tmp_path, sealed):
    """FPROTO-4-05: established by reproduction, with the needle's class named."""
    fx = sealed[0]
    literal = f"export const n = {len(fx.cells)};\n".encode()
    outcome = _run(tmp_path, sealed, builder_extra={"assets/count.js": literal})
    assert outcome.cls == h.COLLISION
    assert outcome.detail == {"file": "assets/count.js", "classes": ["row_count"]}


def test_a_collision_whose_reproduction_differs_is_the_harnesss(tmp_path, sealed):
    fx = sealed[0]
    literal = f"export const n = {len(fx.cells)};\n".encode()
    outcome = _run(tmp_path, sealed, builder_extra={"assets/count.js": literal}, role_override="labels")
    assert outcome.cls == h.HARNESS_ERROR


def test_the_manifest_is_searched_by_its_labels_only(tmp_path, sealed):
    """N83: the manifest's typed fields are not haystack; a label in it would be."""
    assert _run(tmp_path, sealed).cls == h.PASS


# --- archives ------------------------------------------------------------------------


def test_an_archive_is_reproducible_checked_and_never_overwritten(tmp_path):
    src = _builder(tmp_path)
    a = h.archive(src, tmp_path / "a.tar.gz")
    b = h.archive(src, tmp_path / "b.tar.gz")
    assert a == b
    with pytest.raises(FileExistsError):
        h.archive(src, tmp_path / "a.tar.gz")
    h.extract(tmp_path / "a.tar.gz", tmp_path / "out", a)
    assert h.tree(tmp_path / "out") == h.tree(src)
    with pytest.raises(ValueError):
        h.extract(tmp_path / "a.tar.gz", tmp_path / "out2", "0" * 64)


def test_an_archive_keeps_modes_links_and_fifos_and_assembly_carries_them_to_the_gate(tmp_path, sealed):
    """PROTO-1-03: a builder output with a 0664 file, a link and a FIFO comes back
    from its archive as it was, and the FIFO reaches `verify`."""
    fx, pkg, _, _ = sealed
    src = _builder(tmp_path)
    (src / "assets" / "shared.js").write_text("1")
    os.chmod(src / "assets" / "shared.js", 0o664)
    os.symlink("app.js", src / "assets" / "alias.js")
    os.mkfifo(src / "pipe.txt")
    digest = h.archive(src, tmp_path / "b.tar.gz")
    h.extract(tmp_path / "b.tar.gz", tmp_path / "back", digest)
    assert h.tree(tmp_path / "back") == h.tree(src)
    outcome, validated = h.assemble(tmp_path / "back", pkg, fx.rows(), tmp_path / "artifact")
    assert outcome.cls == h.PASS
    result = h.verify(tmp_path / "artifact", tmp_path / "back", h.write_root(tmp_path / "run", _lists(tmp_path)), validated)
    assert h.tree(tmp_path / "back") == h.tree(src)
    assert (result.cls, result.message) == (h.FORM, "assets/alias.js is a symbolic link")


def test_a_fifo_alone_reaches_the_gate_through_the_archive(tmp_path, sealed):
    """PROTO-2-11: the FIFO itself causes the form refusal, with no link before it."""
    fx, pkg, _, _ = sealed
    src = _builder(tmp_path)
    os.mkfifo(src / "pipe.txt")
    digest = h.archive(src, tmp_path / "b.tar.gz")
    h.extract(tmp_path / "b.tar.gz", tmp_path / "back", digest)
    outcome, validated = h.assemble(tmp_path / "back", pkg, fx.rows(), tmp_path / "artifact")
    result = h.verify(tmp_path / "artifact", tmp_path / "back", h.write_root(tmp_path / "run", _lists(tmp_path)), validated)
    assert (result.cls, result.message) == (h.FORM, "pipe.txt is not a plain file")


def test_an_entry_no_archive_can_carry_is_refused_and_recorded(tmp_path, sealed):
    import socket

    fx, pkg, _, _ = sealed
    src = _builder(tmp_path)
    sock = socket.socket(socket.AF_UNIX)
    sock.bind(str(src / "s.sock"))
    try:
        with pytest.raises(trees.Refused, match="s.sock"):
            h.archive(src, tmp_path / "b.tar.gz")
        outcome, _ = h.assemble(src, pkg, fx.rows(), tmp_path / "artifact")
        assert outcome.cls == h.FORM and outcome.detail == {"entries": ["s.sock"]}
    finally:
        sock.close()


# --- verify is bound to what assembly produced (PROTO-1-02) ------------------------------


def test_a_valid_package_of_another_fixture_swapped_in_after_assembly_is_the_harnesss(tmp_path, sealed):
    other, _ = f.generate(SEED + 1)
    totals, parquet = f.payload(other)
    outcome = _run(tmp_path, sealed, after_assembly=lambda a: _replace_package(a, release.profiles(f.HERE), totals, parquet))
    assert outcome.cls == h.PASS  # unbound, the gate passes it: only the binding catches the swap


def test_a_linked_envelope_after_assembly_is_the_harnesss(tmp_path, sealed):
    def link(artifact):
        env = next(p for p in (artifact / "package").iterdir() if p.suffix == ".bice")
        env.unlink()
        os.symlink("/nonexistent", env)

    _run(tmp_path, sealed, after_assembly=link)  # the bound verify's refusal is asserted in _run


def test_a_failure_inside_classification_is_the_harnesss(tmp_path, sealed, monkeypatch):
    def broken(data):
        raise f.SchemaFault("duckdb")

    monkeypatch.setattr(f, "schema_only", broken)
    outcome = _run(tmp_path, sealed, builder_extra={"assets/empty.parquet": f.parquet([])})
    assert outcome.cls == h.HARNESS_ERROR and "schema check failed" in outcome.message
    monkeypatch.undo()

    def unreadable(root):
        raise OSError("disk")

    monkeypatch.setattr(trees, "files", unreadable)
    fx = sealed[0]
    outcome = _run(tmp_path / "b", sealed, builder_extra={"assets/count.js": f"n = {len(fx.cells)};".encode()})
    assert outcome.cls == h.HARNESS_ERROR and "reproduction failed" in outcome.message


def test_a_zero_row_parquet_with_other_types_is_content_not_schema_only(tmp_path, sealed):
    import duckdb
    import tempfile as tf

    con = duckdb.connect()
    cols = ", ".join(f'NULL::VARCHAR AS "{n}"' for n in f.COLUMNS)
    with tf.TemporaryDirectory() as d:
        con.execute(f"COPY (SELECT {cols} WHERE false) TO '{d}/x.parquet' (FORMAT parquet)")
        data = open(f"{d}/x.parquet", "rb").read()
    assert f.schema_only(data) is False
    assert _run(tmp_path, sealed, builder_extra={"assets/wrong.parquet": data}).cls == h.CONTENT


# --- round 2 (PROTO-2-01 to -03, -14) ---------------------------------------------------


def test_a_root_under_a_linked_ancestor_and_a_linked_artifact_are_refused(tmp_path, sealed):
    fx, pkg, _, _ = sealed
    real = tmp_path / "real"
    _builder(real)
    (tmp_path / "via").symlink_to(real)
    with pytest.raises(trees.Refused, match="is a link"):
        trees.entries(tmp_path / "via" / "builder")
    outcome, validated = h.assemble(real / "builder", pkg, fx.rows(), tmp_path / "artifact")
    assert outcome.cls == h.PASS
    (tmp_path / "artifact").rename(tmp_path / "moved")
    (tmp_path / "artifact").symlink_to(tmp_path / "moved")
    result = h.verify(tmp_path / "artifact", real / "builder", h.write_root(tmp_path / "run", _lists(tmp_path)), validated)
    assert result.cls == h.HARNESS_ERROR


def test_an_unreadable_folder_refuses_the_archive_and_the_inspection(tmp_path, sealed):
    import inspect_output as io_

    src = _builder(tmp_path)
    (src / "assets" / "hidden").mkdir()
    (src / "assets" / "hidden" / "x.js").write_text("fixture_canal_a")
    os.chmod(src / "assets" / "hidden", 0)
    try:
        with pytest.raises(trees.Refused, match="cannot read"):
            h.archive(src, tmp_path / "b.tar.gz")
        with pytest.raises(trees.Refused):
            io_.inspect_dir(src, io_.Needles.from_fixture(sealed[0], gate=False))
    finally:
        os.chmod(src / "assets" / "hidden", 0o755)


def test_setgid_and_sticky_bits_survive_the_archive(tmp_path):
    src = _builder(tmp_path)
    os.chmod(src / "assets", 0o1775)
    digest = h.archive(src, tmp_path / "b.tar.gz")
    h.extract(tmp_path / "b.tar.gz", tmp_path / "back", digest)
    assert h.tree(tmp_path / "back") == h.tree(src)


def test_an_absolute_archive_member_is_refused_and_leaves_its_sibling_alone(tmp_path):
    import gzip as gz
    import hashlib
    import io as io_mod
    import tarfile

    sibling = tmp_path / "sibling"
    sibling.mkdir(mode=0o700)
    buf = io_mod.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(str(sibling))
        info.type, info.mode = tarfile.DIRTYPE, 0o755
        tar.addfile(info)
    raw = gz.compress(buf.getvalue())
    (tmp_path / "x.tar.gz").write_bytes(raw)
    with pytest.raises(trees.Refused, match="outside"):
        h.extract(tmp_path / "x.tar.gz", tmp_path / "out", hashlib.sha256(raw).hexdigest())
    assert (sibling.stat().st_mode & 0o777) == 0o700


@pytest.mark.parametrize("rel", ["/abs/marker", "assets/../../marker", "linked/marker"])
def test_a_control_addition_stays_inside_the_artifact(tmp_path, sealed, rel):
    fx, pkg, _, _ = sealed
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    builder = _builder(tmp_path)
    (builder / "linked").symlink_to(sibling)
    outcome, _ = h.assemble(builder, pkg, fx.rows(), tmp_path / "artifact", control_additions={rel.replace("/abs", str(sibling)): b"x"})
    assert outcome.cls == h.HARNESS_ERROR
    assert list(sibling.iterdir()) == []


def test_a_judged_run_refuses_control_evidence_and_the_unbound_gate(tmp_path, sealed):
    fx, pkg, _, _ = sealed
    builder = _builder(tmp_path)
    outcome, validated = h.assemble(builder, pkg, fx.rows(), tmp_path / "artifact", control_additions={"assets/x.txt": b"1"})
    root = h.write_root(tmp_path / "run", _lists(tmp_path))
    assert h.verify(tmp_path / "artifact", builder, root, validated).cls == h.HARNESS_ERROR
    with pytest.raises(ValueError):
        h.run_gate(tmp_path / "artifact", builder, root, validated)


def test_a_collision_reproduced_against_another_builder_is_the_harnesss(tmp_path, sealed):
    fx, pkg, _, _ = sealed
    builder = _builder(tmp_path, {"assets/count.js": f"n = {len(fx.cells)};".encode()})
    outcome, validated = h.assemble(builder, pkg, fx.rows(), tmp_path / "artifact")
    other = tmp_path / "other"
    trees.copy(builder, other)
    (other / "assets" / "extra.js").write_text("1")
    root = h.write_root(tmp_path / "run", _lists(tmp_path))
    assert h.verify(tmp_path / "artifact", builder, root, validated).cls == h.COLLISION
    wrong = h.verify(tmp_path / "artifact", other, root, validated)
    assert wrong.cls == h.HARNESS_ERROR and "not the one assembled" in wrong.message


def test_a_schema_query_whose_file_vanished_is_the_checks_failure(monkeypatch):
    import duckdb

    real = duckdb.DuckDBPyConnection.execute

    def vanish(self, sql, *a):
        if "DESCRIBE" in sql:
            path = sql.split("read_parquet('")[1].split("'")[0]
            os.unlink(path)
        return real(self, sql, *a)

    monkeypatch.setattr(duckdb.DuckDBPyConnection, "execute", vanish)
    with pytest.raises(f.SchemaFault):
        f.schema_only(f.parquet([]))


# --- round 3 (PROTO-3-04) -----------------------------------------------------------


def test_a_schema_query_runtime_fault_on_an_intact_file_is_the_checks_failure(tmp_path, sealed, monkeypatch):
    import duckdb

    real = duckdb.DuckDBPyConnection.execute

    def out_of_memory(self, sql, *a):
        if "/f.parquet')" in sql:  # the schema check's own copy, not the gate's reads
            raise duckdb.OutOfMemoryException("injected")
        return real(self, sql, *a)

    fx, pkg, _, _ = sealed
    builder = _builder(tmp_path, {"assets/empty.parquet": _parquet_with([])})
    _, validated = h.assemble(builder, pkg, fx.rows(), tmp_path / "artifact")
    root = h.write_root(tmp_path / "run", _lists(tmp_path))
    assert h.verify(tmp_path / "artifact", builder, root, validated).cls == h.SCHEMA_ONLY
    with monkeypatch.context() as m:
        m.setattr(duckdb.DuckDBPyConnection, "execute", out_of_memory)
        with pytest.raises(f.SchemaFault):
            f.schema_only(f.parquet([]))
        outcome = h.verify(tmp_path / "artifact", builder, root, validated)
    assert outcome.cls == h.HARNESS_ERROR and "schema check failed" in outcome.message
    assert f.schema_only(b"PAR1" + b"\0" * 40 + b"PAR1") is None  # bytes that do not parse stay the file's


def test_an_empty_builder_output_is_a_snapshot_reproduction_is_bound_to(tmp_path, sealed):
    fx, pkg, _, _ = sealed
    builder = tmp_path / "builder"
    builder.mkdir()
    literal = f"n = {len(fx.cells)};".encode()
    outcome, validated = h.assemble(builder, pkg, fx.rows(), tmp_path / "artifact", control_additions={"count.js": literal})
    assert outcome.cls == h.PASS and validated.builder == ()
    root = h.write_root(tmp_path / "run", _lists(tmp_path))
    assert h.verify(tmp_path / "artifact", builder, root, validated, label="control").cls == h.CONTENT
    other = tmp_path / "other"
    other.mkdir()
    (other / "count.js").write_bytes(literal)
    wrong = h.verify(tmp_path / "artifact", other, root, validated, label="control")
    assert wrong.cls == h.HARNESS_ERROR and "not the one assembled" in wrong.message
