"""The controls of §2.5.5 on a candidate's own builder output
(docs/framework_prototype.md §2.5.5, §7 step 5).

Each control is the candidate's archived builder output, the measured
fixture's validated package and **one** leak, in one carrier, placed by
assembly as a control's addition — or, for the assembly's own form, a copy of
the builder output with a `package/` of its own —; `verify` runs under the
candidate's lists widened by that one file's path and extension, so that it
reaches its own reason, and the inspection with the fixture's needles. Each
asserts its diagnosis at the layer it is for — `verify`'s class, the
inspection's code in that file — and records the rest, the verdict of that
one run included. Control runs are labelled `control` and never enter a
candidate's history.

A control is as expected only when everything it shows is (CMP-1-07): its
`verify` class, its code in the added file — through its decoding layer where
it has one —, no finding anywhere else, nothing inconclusive, and the verdict
of that run alone. The rows of §2.5.5 that take no builder output of a
candidate's — the incidental literal, the numeric label behind form, the
harness classes, the collision, the carrier nobody listed, a pinned body
changed — are proved on hand-made outputs by step 1's tests; A1's carriers of
Evidence's own page, each alone in a clean artifact, by the clear mode's
controls (`clear_mode.py evidence --controls`, step 2).
"""

from __future__ import annotations

import base64
import dataclasses
import gzip
import hashlib
import io
import json
import pathlib
import shutil
import time
from decimal import Decimal

import brotli

import fixture as fx_mod
import harness as h
import inspect_output as io_
import verdict as v
from bi_como_codigo import contract as c

HERE = fx_mod.HERE
NONE = "no finding"


def _js(amount: Decimal) -> str:
    return format(amount.normalize(), "f")


def _ending_in_zero(fx: fx_mod.Fixture) -> Decimal:
    """An amount whose JavaScript spelling is shorter and holds no needle of the gate."""
    values = c.check_payload(fx_mod.contract(), fx_mod.contract().reports[fx_mod.REPORT], *fx_mod.payload(fx))
    gate = c.needles([values], set())
    return next(m.net for _, m in sorted(fx.cells.items()) if m.net.as_tuple().digits[-1] == 0 and m.net.as_tuple().digits[-2] != 0
                and not io_.gate_hits({"x": _js(m.net).encode()}, gate))


def _rows_json(fx: fx_mod.Fixture, n: int = 3) -> bytes:
    return json.dumps([[str(x) if isinstance(x, Decimal) else x for x in r] for r in fx.rows()[:n]]).encode()


def _arrow_counts(fx: fx_mod.Fixture) -> bytes:
    import pyarrow as pa
    import pyarrow.ipc as ipc

    table = pa.table({"order_count": [r[7] for r in fx.rows()[:3]]})  # numbers only: no label for the gate to see
    sink = io.BytesIO()
    with ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.getvalue()


def _parquet_rows(fx: fx_mod.Fixture) -> bytes:
    return fx_mod.parquet(fx.rows()[:1])


@dataclasses.dataclass(frozen=True)
class Control:
    name: str
    additions: dict[str, bytes]
    verify: str  # the class `verify` must give
    code: str  # the inspection's code in the added file, or NONE
    own_package: bool = False  # the builder output carries a package/ of its own: assembly's form
    layers: tuple[str, ...] = ()  # the decoding layers the code's finding must be reached through
    #: What the gate's refusal must say — the added file it names, or the form it refuses —: a refusal
    #: of the class asked for, for another reason, is no control as expected (CMP-3-05).
    reason: str | None = None

    @property
    def expected_verdict(self) -> str:
        if self.code != NONE:
            return v.FAILS
        return v.PASSES if self.verify == h.PASS else v.COST


#: The gate's refusal of a second package manifest (`release._package`).
MANIFESTS = "2 package manifests in the artifact; exactly one is expected"


def table(fx: fx_mod.Fixture) -> list[Control]:
    """§2.5.5's rows that take a candidate's builder output, with the measured fixture."""
    rows = _rows_json(fx)
    amount = _ending_in_zero(fx)
    count = sorted(fx.cells.items())[0][1].order_count
    escaped = "".join(f"\\u{ord(ch):04x}" for ch in "fixture_canal_a")
    d = "bice-control/"
    return [
        Control("clean metadata", {d + "meta.json": b'{"version": 1, "month": 5}'}, h.PASS, NONE),
        Control("a count in a JSON", {d + "count.json": json.dumps({"orders": count}).encode()}, h.CONTENT, io_.INSPECT_NUMBER,
                reason=f"(in {d}count.json)"),
        Control("package only, with a form refusal", {d + "manifest.json": b"{}"}, h.FORM, NONE, reason=MANIFESTS),
        Control("a fixed label", {d + "label.txt": b"fixture_raiz_3"}, h.CONTENT, io_.INSPECT_TEXT, reason=f"(in {d}label.txt)"),
        Control("an amount in pt-BR", {d + "v.js": c.spellings(str(amount))[1].encode()}, h.CONTENT, io_.INSPECT_TEXT, reason=f"(in {d}v.js)"),
        Control("an amount in its JavaScript spelling", {d + "w.js": f"const v = {_js(amount)};".encode()}, h.PASS, io_.INSPECT_NUMBER),
        Control("Arrow IPC", {d + "q.arrow": _arrow_counts(fx)}, h.PASS, io_.INSPECT_ARROW),
        Control("Parquet with rows", {d + "p.parquet": _parquet_rows(fx)}, h.CONTENT, io_.INSPECT_PARQUET,
                reason=f"{d}p.parquet holds a Parquet magic"),
        Control("schema only", {d + "s.parquet": fx_mod.parquet([])}, h.SCHEMA_ONLY, NONE, reason=f"{d}s.parquet holds a Parquet magic"),
        Control("gzip of a JSON of rows", {d + "rows.bin": gzip.compress(rows, mtime=0)}, h.PASS, io_.INSPECT_TEXT, layers=("gzip",)),
        Control("brotli of a JSON of rows", {d + "rows2.bin": brotli.compress(rows)}, h.PASS, io_.INSPECT_TEXT, layers=("brotli",)),
        Control("base64 of a JSON of rows", {d + "rows.txt": base64.b64encode(rows)}, h.PASS, io_.INSPECT_TEXT, layers=("base64",)),
        Control("JSON-escaped text", {d + "s.js": f'const s = "{escaped}";'.encode()}, h.PASS, io_.INSPECT_TEXT, layers=("escapes",)),
        Control("a base64 payload in a service worker", {d + "sw.js": b"self.data = '" + base64.b64encode(gzip.compress(rows, mtime=0)) + b"';"},
                h.PASS, io_.INSPECT_TEXT, layers=("base64", "gzip")),
        Control("a label in a .map", {d + "app.js.map": b'{"sources": ["fixture_canal_a"]}'}, h.FORM, io_.INSPECT_TEXT,
                reason=f"{d}app.js.map is a source map"),
        Control("a label in a second manifest.json", {d + "x/manifest.json": b'{"name": "fixture_canal_a"}'}, h.FORM, io_.INSPECT_TEXT,
                reason=MANIFESTS),
        Control("assembly form: a package/ of the builder's", {}, "assembly FORM", NONE, own_package=True),
    ]


def _lists(candidate: str, additions: dict[str, bytes], out: pathlib.Path) -> pathlib.Path:
    """The candidate's lists, widened by each added file's path and extension."""
    out.mkdir(parents=True)
    src = HERE / "lists" / candidate
    include = (src / "include.txt").read_text(encoding="utf-8") + "".join(f"site/{rel}\n" for rel in additions)
    types = (src / "media_types.txt").read_text(encoding="utf-8")
    known = {line.split()[0] for line in types.splitlines() if line.strip() and not line.startswith("#")}
    for rel in additions:
        ext = pathlib.PurePosixPath(rel).suffix
        if ext and ext not in known:
            types += f"{ext} application/octet-stream\n"
            known.add(ext)
    (out / "include.txt").write_text(include, encoding="utf-8")
    (out / "media_types.txt").write_text(types, encoding="utf-8")
    return out


def run(candidate: str, builder: pathlib.Path, builder_digest: str, package: pathlib.Path, fx: fx_mod.Fixture,
        out: pathlib.Path, *, dependencies: frozenset[str] = frozenset()) -> list[dict]:
    out.mkdir(parents=True, exist_ok=False)
    needles = io_.Needles.from_fixture(fx)
    built = io_.inspect_dir(builder, needles, dependencies=dependencies)
    results = []
    for i, ctl in enumerate(table(fx)):
        work = out / f"c{i:02d}"
        source = builder
        if ctl.own_package:
            source = work / "builder"
            shutil.copytree(builder, source, symlinks=True)
            (source / h.PACKAGE).mkdir()
            (source / h.PACKAGE / "manifest.json").write_bytes(b"{}")
        else:
            work.mkdir()
        assembly, validated = h.assemble(source, package, fx.rows(), work / "artifact", control_additions=ctl.additions or None)
        row = {"control": ctl.name, "assembly": assembly.cls, "expected_verify": ctl.verify, "expected_code": ctl.code,
               "expected_verdict": ctl.expected_verdict}
        stages = {"build": v.Stage(), "archive": v.Stage(),
                  "inspect_builder": v.Stage(findings=len(built.findings), inconclusive=len(built.inconclusive)),
                  "assembly": v.Stage(cls=assembly.cls)}
        artifact_digest = None
        if assembly.cls == h.PASS:
            started = time.time()
            checked = h.verify(work / "artifact", source, h.write_root(work, _lists(candidate, ctl.additions, work / "lists")), validated,
                               label="control")
            row["verify_seconds"] = round(time.time() - started, 3)  # the gate's time, measured (CMP-1-12)
            # Assembly proved the rest of the artifact byte for byte the builder output, inspected once
            # above: what is new is the control's file and the package, inspected here.
            added = set(ctl.additions)
            new = [io_.Item(rel, (work / "artifact" / rel).read_bytes()) for rel in sorted(added)]
            new += [io_.Item(f"{h.PACKAGE}/{name}", (work / "artifact" / h.PACKAGE / name).read_bytes()) for name in sorted(validated.files)]
            inspected = io_.inspect_items(new, needles, validated=dict(validated.files), dependencies=dependencies)
            in_file = sorted({x.code for x in inspected.findings if x.file in added})
            through = any(x.code == ctl.code and x.file in added and all(f"> {layer}" in x.path for layer in ctl.layers)
                          for x in inspected.findings)
            stages["verify"] = v.Stage(cls=checked.cls)
            stages["inspect_artifact"] = v.Stage(findings=len(inspected.findings) + len(built.findings),
                                                 inconclusive=len(inspected.inconclusive) + len(built.inconclusive))
            artifact_digest = hashlib.sha256(json.dumps(h.tree(work / "artifact")).encode()).hexdigest()
            row.update(verify=checked.cls, verify_message=checked.message[:300], codes_in_file=in_file,
                       codes_elsewhere=sorted({x.code for x in [*inspected.findings, *built.findings] if x.file not in added}),
                       inconclusive=len(inspected.inconclusive) + len(built.inconclusive))
            row["as_expected"] = (checked.cls == ctl.verify and (ctl.reason is None or ctl.reason in checked.message)
                                  and (in_file == [] if ctl.code == NONE else ctl.code in in_file and through)
                                  and row["codes_elsewhere"] == [] and row["inconclusive"] == 0)
        else:
            row["as_expected"] = (ctl.verify == f"assembly {assembly.cls}" and not built.findings and not built.inconclusive)
            row.update(inspect_builder_findings=len(built.findings), inconclusive=len(built.inconclusive))
        judged = v.verdict([v.Record(f"control{i}", label="judged", build_input="control", builder_digest=builder_digest,
                                     artifact_digest=artifact_digest, stages=stages)])  # this one run, judged alone
        row["verdict"] = judged.name
        row["as_expected"] = row["as_expected"] and judged.name == ctl.expected_verdict
        shutil.rmtree(work / "artifact", ignore_errors=True)
        shutil.rmtree(work / "builder", ignore_errors=True)
        results.append(row)
    (out / "controls.json").write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return results

