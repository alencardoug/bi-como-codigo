"""The comparison of stage 2.3, from one entry point (docs/framework_prototype.md
§5, §6, §7; FPROTO-5-08): `make prototype`.

It builds what is missing — each candidate's encrypted route at the harness
that runs, `route.py` —, draws the measured fixture once against both builder
outputs and carries both runs through (`measured.py`), and then, on both
artifacts of that draw: the browser check and its proofs (`check.py`, the G
mutant for B), the controls of §2.5.5 on each candidate's own builder output
(`builder_controls.py`), the browser diagnostic (`diagnose.py`, N96: reported, never
judged), the measures of §2.7 (`measure.py`) and what needs no browser. Every
result is kept with the package's and the artifact's digests; the state's
measures are discarded with the draw by any build or harness change
(`route.py`). The verdicts are the records' (§2.5.4).

    uv run --frozen --group prototype python prototypes/framework/compare.py --commit <sha>
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import secrets
import subprocess

import builder_controls
import cdn
import check
import diagnose
import fixture as fx_mod
import inspect_output as io_
import measure
import measured
import route

HERE = route.HERE


def _fixture(draw: dict, *, mutant: bool = False) -> fx_mod.Fixture:
    folder = measured.MEASURED / (draw["id"] + ("-mutant" if mutant else ""))
    return fx_mod.Fixture.load(json.loads((folder / "cells.json").read_text(encoding="utf-8")))


def build_missing(commit: str) -> list[str]:
    """Each candidate built again unless its archived builder output is of this
    harness; returns the candidates built."""
    state = route.load()
    inputs = route.harness_inputs(commit)
    built = []
    for name, build in (("own", route.build_own), ("evidence", route.build_evidence)):
        entry = state["builds"].get(name)
        if state["harness"] != inputs or not entry or entry.get("status") != "archived" or entry.get("harness") != inputs:
            result = build(commit)
            if result["status"] != "archived":
                raise route.Refused(f"{name}'s build ended {result['status']}")
            built.append(name)
            state = route.load()
    return built


def measure_candidate(name: str, draw: dict, artifacts: dict, out: pathlib.Path) -> dict:
    fx = _fixture(draw)
    artifact = route.RUNS / artifacts[name]["artifact"]
    result = {"package": draw["package"], "artifact_digest": artifacts[name]["artifact_digest"], "fixture_digest": draw["fixture_digest"]}
    mutant = {}
    if name == "own" and "own-mutant" in artifacts:
        mutant = {"mutant_artifact": route.RUNS / artifacts["own-mutant"]["artifact"], "mutant": _fixture(draw, mutant=True)}
    result["check"] = check.run(name, artifact, fx, out / "check", **mutant)
    state = route.load()
    entry = state["builds"][name]
    result["controls"] = builder_controls.run(name, route.RUNS / "draws" / draw["id"] / name / "builder", entry["builder_digest"],
                                              measured.MEASURED / draw["id"] / "package", fx, out / "controls",
                                              dependencies=measured._dependencies(name, entry, route.RUNS))
    decl = HERE / name / "cdn.json"
    pins = {f["url"]: f["sha256"] for f in json.loads(decl.read_text(encoding="utf-8"))["files"]}
    diagnosis = diagnose.run(artifact, io_.Needles.from_fixture(fx), out=out / "diagnostic", cdn=pins,
                             fulfill=cdn.bodies(decl, route.RUNS / "cdn_bodies"), validated=dict(draw["package"]))
    result["diagnostic"] = {"leads": diagnosis.leads(), **dataclasses.asdict(diagnosis)}
    expected = check.expected(fx).summary[check.ALL]
    result["measures"] = measure.run(artifact, expected, out / "measures")
    state = route.load()
    entry = state["builds"][name]
    result["static"] = {"lines": measure.lines(name), "gate_lists": measure.gate_lists(name),
                        "dependencies": measure.dependencies(name, entry, route.RUNS),
                        "build": measure.build_measures(entry, route.RUNS / "draws" / draw["id"] / name / "builder"),
                        "upkeep": measure.upkeep(name)}
    return result


@route.serialized
def run(commit: str, *, seed: int | None = None) -> dict:
    built = build_missing(commit)
    state = route.load()
    if state["draw"] is None:
        measured.run(commit, seed if seed is not None else secrets.randbelow(2**31))
        state = route.load()
    draw = state["draw"]
    report = {"commit": commit, "built": built, "draw": {k: v for k, v in draw.items() if k not in ("package", "mutant_package")}}
    if draw["status"] != "clean":
        report["verdicts"] = measured.verdicts(state)
        return report
    out = route.RUNS / "draws" / draw["id"] / "results"
    results = {}
    for name in measured.CANDIDATES:
        kept = state["measures"].get(name)
        if kept and kept.get("artifact_digest") == state["artifacts"][name]["artifact_digest"]:
            results[name] = kept
            continue
        results[name] = measure_candidate(name, draw, state["artifacts"], out / name)
        state = route.load()
        state["measures"][name] = {"artifact_digest": results[name]["artifact_digest"], "results": str((out / name).relative_to(route.RUNS))}
        route.save(state)
        (out / name / "result.json").write_text(json.dumps(results[name], indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    report["verdicts"] = measured.verdicts(route.load())
    report["artifacts"] = {n: {k: v for k, v in a.items() if k not in ("builder_inspection", "artifact_inspection")} for n, a in state["artifacts"].items()}
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--commit", default=None, help="the commit whose harness runs; HEAD by default")
    parser.add_argument("--seed", type=int, help="the draw's seed, if a draw is made; at random and recorded otherwise")
    args = parser.parse_args()
    commit = args.commit or subprocess.run(["git", "-C", str(route.REPO), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    print(json.dumps(run(commit, seed=args.seed), indent=1, ensure_ascii=False, default=str))
