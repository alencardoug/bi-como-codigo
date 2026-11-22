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

Any later build of either candidate, or a change of the harness, discards
the draw and both artifacts (`route.py`); this module refuses to draw again
over a draw that stands.

    uv run --frozen --group prototype python prototypes/framework/measured.py --commit <sha> --seed <n>
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import secrets
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
    state = route.load(runs)
    inputs = route.harness_inputs(commit, require_clean=require_clean)
    if state["harness"] != inputs:
        raise route.Refused("the state's harness is not this one: build both candidates again at it first")
    if state["draw"] is not None:
        raise route.Refused("a draw stands: the measured fixture is drawn once; a build of either candidate discards it")
    entries = {}
    for name in candidates:
        entry = state["builds"].get(name)
        if not entry or entry.get("status") != "archived":
            raise route.Refused(f"no archived builder output of {name}")
        if entry["harness"] != inputs:
            raise route.Refused(f"{name}'s builder output was built at another harness: build it again")
        entries[name] = entry

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
        for name, entry in entries.items():
            # No fixture to inspect the builder output with: the draw's record is its evidence (§2.1, step 4).
            # Bound to the archive it searched, extracted against its digest above (CMP-1-04).
            state["records"].append(dataclasses.asdict(v.Record(f"{draw_id}-{name}", kind="resume",
                                                                builder_digest=entry["builder_digest"], draw_exhausted=exhausted,
                                                                draw_stopped=not exhausted)))
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
    (mutant_dir / "cells.json").write_text(json.dumps(mutant.dump()) + "\n", encoding="utf-8")

    needles = io_.Needles.from_fixture(fx)
    artifacts = {}
    for name, entry in entries.items():
        folder = work / name
        built = io_.inspect_dir(builders[name], needles, dependencies=deps[name])
        stages = {"inspect_builder": _stage(built)}
        result = {"builder_inspection": _summary(built)}
        assembly, validated = h.assemble(builders[name], fixture_dir / "package", fx.rows(), folder / "artifact")
        stages["assembly"] = v.Stage(cls=assembly.cls)
        result["assembly"] = {"class": assembly.cls, "message": assembly.message}
        artifact_digest = None
        if assembly.cls == h.PASS:
            artifact_digest = h.archive(folder / "artifact", folder / "artifact.tar.gz")
            checked = h.verify(folder / "artifact", builders[name], h.write_root(folder, LISTS / name), validated)
            stages["verify"] = v.Stage(cls=checked.cls)
            result["verify"] = {"class": checked.cls, "message": checked.message}
            inspected = io_.inspect_dir(folder / "artifact", needles, validated=dict(validated.files), dependencies=deps[name])
            stages["inspect_artifact"] = _stage(inspected)
            result["artifact_inspection"] = _summary(inspected)
            result["artifact"] = str((folder / "artifact").relative_to(runs))
            result["artifact_archive"] = str((folder / "artifact.tar.gz").relative_to(runs))
            files = [p for p in (folder / "artifact").rglob("*") if p.is_file()]
            result["artifact_files"], result["artifact_bytes"] = len(files), sum(p.stat().st_size for p in files)
        result["artifact_digest"] = artifact_digest
        state["records"].append(dataclasses.asdict(v.Record(
            f"{draw_id}-{name}", kind="resume", builder_digest=entry["builder_digest"], artifact_digest=artifact_digest,
            stages=stages, draw_clean=True, fixture=out["fixture_digest"])))
        artifacts[name] = result
    if "own" in entries:  # the G mutant, for B's browser check (§2.6): a control, never judged
        folder = work / "own-mutant"
        folder.mkdir()
        assembly, _ = h.assemble(builders["own"], mutant_dir / "package", mutant.rows(), folder / "artifact")
        artifacts["own-mutant"] = {"label": "control", "assembly": {"class": assembly.cls, "message": assembly.message},
                                   "artifact": str((folder / "artifact").relative_to(runs)), "fixture_digest": mutant.digest()}
    out["finished"] = route._now()
    state["draw"], state["artifacts"] = out, artifacts
    route.save(state, runs)
    return out


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
