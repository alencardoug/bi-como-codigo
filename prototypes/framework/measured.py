"""The measured fixture and both artifacts (docs/framework_prototype.md §2.1,
§2.2, §2.5, §7 step 4).

Once both candidates' builder outputs are final and built at the harness that
runs, the draw runs **once** against both, with both inspections
(`calibrate.py`). A clean draw gives the measured fixture: it is written,
with its package, under `clear/measured/` — never bound into a sandbox —, its
G mutant derived and sealed beside it, and each candidate's run is carried
through the rest of its stages on its archived builder output: the
inspection of the builder output with the fixture's needles, assembly with
the validated package, `verify` under the candidate's own lists
(`lists/<candidate>/`), and the inspection of the artifact. Each is appended
to the state as a resume of that candidate's build, bound to the fixture by
its digest; the mutant's artifact, for B's browser check, is a control and
stays out of the records. An exhausted or stopped draw is recorded as such.

Each stage is kept in the state as it completes — the clean draw first,
unfinished —, recorded as interrupted before it runs, and the harness is
checked again before its outcome is recorded: an interruption loses nothing
that completed, and the next invocation carries the runs on over the same
sealed fixture, in resumes of their own (CMP-2-01, CMP-2-02).

Any later build of either candidate, or a change of the harness, discards
the draw and both artifacts (`route.py`); this module refuses to draw again
over a draw that stands.

    uv run --frozen --group prototype python prototypes/framework/measured.py --commit <sha> --seed <n>
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import secrets
import shutil
import time

import allowlist as al
import calibrate
import fixture as fx_mod
import harness as h
import inspect_output as io_
import route
import trees
import verdict as v

HERE = route.HERE
MEASURED = HERE / "clear" / "measured"
LISTS = HERE / "lists"
CANDIDATES = ("own", "evidence")


def _stage(report: io_.Report) -> v.Stage:
    return v.Stage(findings=len(report.findings), inconclusive=len(report.inconclusive))


def _dependencies(candidate: str, entry: dict, runs: pathlib.Path) -> frozenset[str]:
    """The digests of the candidate's kept install, which its build read: a
    binary identical to one of them is recorded, not inconclusive (§2.5.2)."""
    kept = runs / candidate / entry["id"] / "node_modules"
    return frozenset(x.sha256 for x in al.files(kept, "node_modules/").entries) if kept.is_dir() else frozenset()


def _summary(report: io_.Report) -> dict:
    by_file: dict[str, dict[str, int]] = {}
    for f in report.findings:
        codes = by_file.setdefault(f.file, {})
        codes[f.code] = codes.get(f.code, 0) + 1
    return {"findings_by_file": dict(sorted(by_file.items())),
            "inconclusive": [{"file": n.file, "path": n.path, "reason": n.reason} for n in report.inconclusive],
            "recorded": len(report.recorded)}


@route.serialized
def run(commit: str, seed: int, *, runs: pathlib.Path = route.RUNS, measured: pathlib.Path = MEASURED,
        candidates: tuple[str, ...] = CANDIDATES, require_clean: bool = True, limit: int = fx_mod.DRAWS_MAX) -> dict:
    """The draw, once, and both runs carried through it — or, over a clean draw
    an interruption left unfinished, its runs carried on from the stages still
    open, on the same sealed fixture (CMP-2-01)."""
    state = route.load(runs)
    inputs = route.harness_inputs(commit, require_clean=require_clean)
    if state["harness"] != inputs:
        raise route.Refused("the state's harness is not this one: build both candidates again at it first")
    standing = state["draw"]
    if standing is not None and (standing.get("status") != "clean" or standing.get("finished")):
        raise route.Refused("a draw stands: the measured fixture is drawn once; a build of either candidate discards it")
    entries = {}
    for name in candidates:
        entry = state["builds"].get(name)
        if not entry or entry.get("status") != "archived":
            raise route.Refused(f"no archived builder output of {name}")
        if entry["harness"] != inputs:
            raise route.Refused(f"{name}'s builder output was built at another harness: build it again")
        if standing is not None and standing["builders"].get(name) != entry["builder_digest"]:
            raise route.Refused(f"the unfinished draw was not made against {name}'s archived builder output")
        entries[name] = entry
    if standing is not None:
        return _carry(state, standing, entries, commit, inputs, runs, measured, require_clean)

    draw_id = f"draw-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(4)}"
    work = runs / "draws" / draw_id
    builders, deps = {}, {}
    for name, entry in entries.items():
        builders[name] = work / name / "builder"
        trees.extract(runs / entry["archive"], builders[name], entry["builder_digest"])  # inspected from the archive
        deps[name] = _dependencies(name, entry, runs)

    t0 = time.time()
    out: dict = {"id": draw_id, "seed": seed, "commit": commit, "harness": inputs, "started": route._now(),
                 "builders": {n: e["builder_digest"] for n, e in entries.items()}}
    try:
        fx, record = calibrate.draw_against(seed, builders, dependencies=deps, limit=limit)
    except (fx_mod.DrawExhausted, fx_mod.DrawStopped) as ended:
        exhausted = isinstance(ended, fx_mod.DrawExhausted)
        record = ended.record or {}
        out.update(status="exhausted" if exhausted else "stopped", seconds=round(time.time() - t0, 1),
                   draws=record.get("draws"), rejections=len(record.get("rejections", [])), stopped=record.get("stopped"),
                   reasons=None if exhausted else ended.reasons)
        (work / "draw.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        route.still(commit, inputs, require_clean=require_clean)  # CMP-2-02
        for name, entry in entries.items():
            # No fixture to inspect the builder output with: the draw's record is its evidence (§2.1, step 4).
            # Bound to the archive it searched, extracted against its digest above (CMP-1-04).
            state["records"].append(dataclasses.asdict(v.Record(f"{draw_id}-{name}", kind="resume",
                                                                builder_digest=entry["builder_digest"], draw_exhausted=exhausted,
                                                                draw_stopped=not exhausted)))
        out["finished"] = route._now()
        state["draw"] = out
        route.save(state, runs)
        return out
    out.update(status="clean", seconds=round(time.time() - t0, 1), draws=record["draws"],
               rejections=len(record["rejections"]), fixture=record["fixture"], fixture_digest=fx.digest())
    (work / "draw.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")

    fixture_dir = measured / draw_id
    out["package"] = fx_mod.write(fx, fixture_dir)["package"]
    (fixture_dir / "cells.json").write_text(json.dumps(fx.dump()) + "\n", encoding="utf-8")
    mutant = fx_mod.mutant(fx)
    mutant_dir = measured / f"{draw_id}-mutant"
    out["mutant_package"] = fx_mod.write(mutant, mutant_dir)["package"]
    out["mutant_digest"] = mutant.digest()
    (mutant_dir / "cells.json").write_text(json.dumps(mutant.dump()) + "\n", encoding="utf-8")
    # Each seal archived beside the draw, by its digest: a resume assembles from these bytes, never from a
    # package sealed again from the same cells, which is another package (CMP-3-02).
    for key, folder in (("package_archive", fixture_dir), ("mutant_package_archive", mutant_dir)):
        archive = work / f"{key}.tar.gz"
        out[key] = {"path": str(archive.relative_to(runs)), "digest": trees.archive(folder / "package", archive)}
    route.still(commit, inputs, require_clean=require_clean)  # CMP-2-02
    # The clean draw is kept at once, unfinished: an interruption from here on loses no stage that
    # completed, and the next invocation carries the runs on over this fixture (CMP-2-01).
    for name, entry in entries.items():
        state["records"].append(dataclasses.asdict(v.Record(f"{draw_id}-{name}", kind="resume", builder_digest=entry["builder_digest"],
                                                            draw_clean=True, fixture=out["fixture_digest"])))
    state["draw"], state["artifacts"] = out, {}
    route.save(state, runs)
    return _carry(state, out, entries, commit, inputs, runs, measured, require_clean)


def _load_fixture(folder: pathlib.Path, digest: str) -> fx_mod.Fixture:
    fx = fx_mod.Fixture.load(json.loads((folder / "cells.json").read_text(encoding="utf-8")))
    if fx.digest() != digest:
        raise route.Refused(f"{folder / 'cells.json'} is not the fixture the draw recorded")
    return fx


def _done_stages(state: dict, draw_id: str, name: str) -> tuple[dict[str, v.Stage], str | None]:
    """The stages of this draw's runs of `name` that completed, and the artifact assembled. A
    stage that ended in `HARNESS_ERROR` or `COLLISION` did not complete: it is run again
    (CMP-3-01); a `verify` run again is followed by the artifact's inspection again, which counts
    only after it (§2.5.4)."""
    done, artifact = {}, None
    for r in route.records(state):
        if not (r.id.startswith(f"{draw_id}-") and r.id.endswith(f"-{name}")):
            continue
        for stage in (s for s in v.STAGES if s in r.stages):  # in the stages' order: the state stores keys sorted
            st = r.stages[stage]
            if stage == "verify":
                done.pop("inspect_artifact", None)  # an inspection counts only after the verify before it
            if st.status == "done" and st.cls not in (h.HARNESS_ERROR, h.COLLISION):
                done[stage] = st
                if stage == "assembly":
                    artifact = r.artifact_digest
    return done, artifact


def _through(done: dict[str, v.Stage]) -> bool:
    """A run through this draw: its assembly refused by form, or its artifact verified and inspected."""
    return ("assembly" in done and done["assembly"].cls == h.FORM) or ("verify" in done and "inspect_artifact" in done)


def _seal(draw: dict, key: str, legacy: pathlib.Path, dest: pathlib.Path, runs: pathlib.Path) -> pathlib.Path:
    """The draw's seal — its package, or the mutant's —, extracted fresh from its archive against its
    digest, and its files the draw's package map exactly (CMP-3-02)."""
    archive = draw.get(f"{key}_archive")
    if archive is not None:
        trees.extract(runs / archive["path"], dest, archive["digest"])
    else:  # a draw before seals were archived: the expanded copy, held to the same map
        shutil.copytree(legacy, dest)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir() if p.is_file()}
    if files != draw[key]:
        raise route.Refused(f"{dest} is not the {key.replace('_', ' ')} the draw sealed")
    return dest


def _carry(state: dict, draw: dict, entries: dict, commit: str, inputs: dict, runs: pathlib.Path, measured: pathlib.Path,
           require_clean: bool) -> dict:
    """Each candidate's run through the stages it has not completed on this draw: the
    builder output's inspection, assembly, `verify`, the artifact's inspection. Each stage is
    recorded as interrupted before it runs and with its outcome after, the harness checked
    again first (CMP-2-01, CMP-2-02); the G mutant for B, a control, last."""
    draw_id = draw["id"]
    fixture_dir = measured / draw_id
    fx = _load_fixture(fixture_dir, draw["fixture_digest"])  # the cells, for the needles and the rows; the package is the seal
    needles = io_.Needles.from_fixture(fx)
    began = state["artifacts"] or any(r["stages"] for r in state["records"] if r["id"].startswith(f"{draw_id}-"))
    attempt = len(list((runs / "draws" / draw_id).glob("attempt-*"))) + 1 if began else 0
    # The first attempt works beside the draw, as before; each later one in a folder of its own.
    work = runs / "draws" / draw_id / (f"attempt-{attempt}" if attempt else "")
    artifacts = state["artifacts"]

    def staged(rec: dict, stage: str, fn):
        rec["stages"][stage] = dataclasses.asdict(v.Stage(status="interrupted"))
        route.save(state, runs)
        outcome = fn()
        route.still(commit, inputs, require_clean=require_clean)
        rec["stages"][stage] = dataclasses.asdict(outcome)
        route.save(state, runs)

    package = None
    for name, entry in entries.items():
        done, artifact_digest = _done_stages(state, draw_id, name)
        if _through(done):
            continue
        if package is None:
            package = _seal(draw, "package", fixture_dir / "package", work / "seal" / "package", runs)
        rec = next(r for r in state["records"] if r["id"] == f"{draw_id}-{name}")
        if rec["stages"]:
            # An earlier attempt began this run: carried on in a resume of its own, which keeps the clean
            # draw — the earlier record's walk may have stopped before it (CMP-3-01).
            rec = dataclasses.asdict(v.Record(f"{draw_id}-r{attempt}-{name}", kind="resume", builder_digest=entry["builder_digest"],
                                              artifact_digest=artifact_digest, draw_clean=True, fixture=draw["fixture_digest"]))
            state["records"].append(rec)
        folder = work / name
        builder = folder / "builder"
        if not builder.exists():  # the draw's own extraction, in its first attempt, is reused
            trees.extract(runs / entry["archive"], builder, entry["builder_digest"])
        deps = _dependencies(name, entry, runs)
        result = artifacts.setdefault(name, {})
        if "inspect_builder" not in done:
            def inspect_builder():
                built = io_.inspect_dir(builder, needles, dependencies=deps)
                result["builder_inspection"] = _summary(built)
                return _stage(built)
            staged(rec, "inspect_builder", inspect_builder)
        bound: dict = {}
        if "assembly" not in done:
            def assembly():
                outcome, bound["validated"] = h.assemble(builder, package, fx.rows(), folder / "artifact")
                result["assembly"] = {"class": outcome.cls, "message": outcome.message}
                if outcome.cls == h.PASS:
                    rec["artifact_digest"] = result["artifact_digest"] = h.archive(folder / "artifact", folder / "artifact.tar.gz")
                    result["artifact"] = str((folder / "artifact").relative_to(runs))
                    result["artifact_archive"] = str((folder / "artifact.tar.gz").relative_to(runs))
                    files = [p for p in (folder / "artifact").rglob("*") if p.is_file()]
                    result["artifact_files"], result["artifact_bytes"] = len(files), sum(p.stat().st_size for p in files)
                else:
                    result["artifact_digest"] = None
                return v.Stage(cls=outcome.cls)
            staged(rec, "assembly", assembly)
            if result["assembly"]["class"] != h.PASS:
                continue
            validated = bound["validated"]
        else:
            # The artifact assembled before, from its archive and against its digest — the tree the
            # assembly bound, since the archive is of that tree —, its package validated again from the
            # artifact's own package/, which must be the draw's seal (CMP-3-02).
            trees.extract(runs / result["artifact_archive"], folder / "artifact", result["artifact_digest"])
            validated = dataclasses.replace(h.validate_package(folder / "artifact" / h.PACKAGE, fx.rows()),
                                            artifact=tuple(h.tree(folder / "artifact")), builder=tuple(h.tree(builder)))
            if validated.files != draw["package"]:
                raise route.Refused(f"{name}'s archived artifact does not hold the package the draw sealed")
        if "verify" not in done:
            def verify():
                started = time.time()
                checked = h.verify(folder / "artifact", builder, h.write_root(folder, LISTS / name), validated)
                # the gate's time on this artifact, measured where it runs (CMP-1-12)
                result["verify"] = {"class": checked.cls, "message": checked.message, "seconds": round(time.time() - started, 3)}
                return v.Stage(cls=checked.cls)
            staged(rec, "verify", verify)

        def inspect_artifact():
            inspected = io_.inspect_dir(folder / "artifact", needles, validated=dict(validated.files), dependencies=deps)
            result["artifact_inspection"] = _summary(inspected)
            return _stage(inspected)
        staged(rec, "inspect_artifact", inspect_artifact)
    if "own" in entries and "artifact_archive" not in artifacts.get("own-mutant", {}):
        # the G mutant, for B's browser check (§2.6): a control, never judged
        mutant_dir = measured / f"{draw_id}-mutant"
        mutant = _load_fixture(mutant_dir, draw["mutant_digest"]) if "mutant_digest" in draw else fx_mod.mutant(fx)
        folder = work / "own-mutant"
        folder.mkdir(parents=True)
        builder = folder / "builder"
        trees.extract(runs / entries["own"]["archive"], builder, entries["own"]["builder_digest"])
        sealed = _seal(draw, "mutant_package", mutant_dir / "package", folder / "seal", runs)
        assembly, _ = h.assemble(builder, sealed, mutant.rows(), folder / "artifact")
        shutil.rmtree(builder)
        artifacts["own-mutant"] = {"label": "control", "assembly": {"class": assembly.cls, "message": assembly.message},
                                   "fixture_digest": mutant.digest()}
        if assembly.cls == h.PASS:  # archived as the candidates' artifacts are, and used from the archive (CMP-1-05)
            artifacts["own-mutant"].update(artifact=str((folder / "artifact").relative_to(runs)),
                                           artifact_archive=str((folder / "artifact.tar.gz").relative_to(runs)),
                                           artifact_digest=h.archive(folder / "artifact", folder / "artifact.tar.gz"))
        route.still(commit, inputs, require_clean=require_clean)
    # Finished only when every run is through it; otherwise it stays open, and the next invocation
    # carries on what errored (CMP-3-01).
    open_ = [n for n in entries if not _through(_done_stages(state, draw_id, n)[0])]
    if open_:
        draw["open"] = open_
    else:
        draw.pop("open", None)
        draw["finished"] = route._now()
    state["draw"] = draw
    route.save(state, runs)
    return draw


def verdicts(state: dict) -> dict[str, str]:
    """Each candidate's verdict over its own judged records (§2.5.4)."""
    out = {}
    for name in CANDIDATES:
        entry = state["builds"].get(name)
        if not entry:
            continue
        prefix = f"{name}-"
        mine = [r for r in route.records(state) if r.id.startswith(prefix) or r.id.endswith(f"-{name}")]
        judged = v.verdict(mine)
        out[name] = f"{judged.name}: {judged.reason}"
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--commit", required=True, help="the commit whose harness runs, as the builds were")
    parser.add_argument("--seed", type=int, help="the draw's seed; drawn at random and recorded when omitted")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbelow(2**31)
    result = run(args.commit, seed)
    state = route.load()
    print(json.dumps({**result, "verdicts": verdicts(state)}, indent=1, default=str))
    raise SystemExit(0 if result["status"] == "clean" else 1)
