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
import hashlib
import json
import pathlib
import secrets
import shutil
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
import trees

HERE = route.HERE


def _fixture(draw: dict, *, mutant: bool = False, digest: str | None = None) -> fx_mod.Fixture:
    """The drawn fixture — or its mutant —, checked against the digest the draw recorded (CMP-1-05)."""
    folder = measured.MEASURED / (draw["id"] + ("-mutant" if mutant else ""))
    fx = fx_mod.Fixture.load(json.loads((folder / "cells.json").read_text(encoding="utf-8")))
    if digest is not None and fx.digest() != digest:
        raise route.Refused(f"{folder / 'cells.json'} is not the fixture the draw recorded")
    return fx


def _bound(runs: pathlib.Path, archive: str, digest: str, dest: pathlib.Path) -> pathlib.Path:
    """A fresh extraction of an archive, its digest checked first: what is checked and measured
    is the archived tree, never a folder left beside it that could have changed (CMP-1-05)."""
    trees.extract(runs / archive, dest, digest)
    return dest


def build_missing(commit: str, runs: pathlib.Path = route.RUNS) -> list[str]:
    """Each candidate built again unless its archived builder output is of this
    harness; returns the candidates built."""
    state = route.load(runs)
    inputs = route.harness_inputs(commit)
    built = []
    for name, build in (("own", route.build_own), ("evidence", route.build_evidence)):
        entry = state["builds"].get(name)
        if state["harness"] != inputs or not entry or entry.get("status") != "archived" or entry.get("harness") != inputs:
            result = build(commit, runs=runs)
            if result["status"] != "archived":
                raise route.Refused(f"{name}'s build ended {result['status']}")
            built.append(name)
            state = route.load(runs)
    return built


def measure_candidate(name: str, draw: dict, artifacts: dict, out: pathlib.Path, runs: pathlib.Path = route.RUNS) -> dict:
    """Everything on one candidate's artifact, in a fresh folder: a retry after a failure starts
    again instead of meeting the earlier attempt's output (CMP-1-05)."""
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    fx = _fixture(draw, digest=draw["fixture_digest"])
    entry = route.load(runs)["builds"][name]
    art = artifacts[name]
    artifact = _bound(runs, art["artifact_archive"], art["artifact_digest"], out / "bound" / "artifact")
    held = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (artifact / "package").iterdir() if p.is_file()}
    if held != draw["package"]:  # measured and labelled with the draw's package only when it is the one it holds (CMP-3-02)
        raise ValueError(f"{name}'s artifact does not hold the package the draw sealed")
    builder = _bound(runs, entry["archive"], entry["builder_digest"], out / "bound" / "builder")
    result = {"package": draw["package"], "artifact_digest": art["artifact_digest"], "fixture_digest": draw["fixture_digest"],
              "draw": draw["id"], "harness": draw["harness"]}
    mutant = {}
    if name == "own":
        m = artifacts.get("own-mutant", {})
        if "artifact_archive" in m:
            try:  # the mutant is B's proof alone: a mutant that does not bind is a proof missing (CMP-3-06)
                mutant = {"mutant_artifact": _bound(runs, m["artifact_archive"], m["artifact_digest"], out / "bound" / "mutant"),
                          "mutant": _fixture(draw, mutant=True, digest=m["fixture_digest"])}
            except (route.Refused, ValueError, OSError) as refusal:
                mutant = {}
                result["mutant_missing"] = f"B's G mutant does not bind: {refusal}"[:500]
        else:  # the check runs, and says its mutant proof is missing; the rest is measured (CMP-2-05)
            result["mutant_missing"] = f"B's G mutant has no artifact: assembly {m.get('assembly')}"
    result["check"] = check.run(name, artifact, fx, out / "check", **mutant)
    # The controls take the package the artifact holds — the archived one, by its digest —, never the
    # expanded copy beside the draw, which could have been sealed again (CMP-2-05).
    result["controls"] = builder_controls.run(name, builder, entry["builder_digest"], artifact / "package", fx,
                                              out / "controls", dependencies=measured._dependencies(name, entry, runs))
    decl = HERE / name / "cdn.json"
    pins = {f["url"]: f["sha256"] for f in json.loads(decl.read_text(encoding="utf-8"))["files"]}
    diagnosis = diagnose.run(artifact, io_.Needles.from_fixture(fx), out=out / "diagnostic", cdn=pins,
                             fulfill=cdn.bodies(decl, runs / "cdn_bodies"), validated=dict(draw["package"]))
    result["diagnostic"] = {"leads": diagnosis.leads(), **dataclasses.asdict(diagnosis)}
    expected = check.expected(fx).summary[check.ALL]
    result["measures"] = measure.run(artifact, expected, out / "measures")
    result["static"] = {"lines": measure.lines(name), "gate_lists": measure.gate_lists(name),
                        "dependencies": measure.dependencies(name, entry, runs),
                        "build": measure.build_measures(entry, builder),
                        "upkeep": measure.upkeep(name)}
    shutil.rmtree(out / "bound")  # the archives stay; their extractions are not kept
    return result


#: What a measured result holds, every part with the shape the report reads (CMP-3-06).
_PARTS = {"check": dict, "controls": list, "diagnostic": dict, "measures": dict, "static": dict, "package": dict}


def _complete(result: dict) -> bool:
    return all(isinstance(result.get(k), kind) for k, kind in _PARTS.items()) and "passed" in result["check"]


def _kept(state: dict, name: str, runs: pathlib.Path) -> dict | None:
    """A measured result reused only when its file exists, reads, and is of this artifact, this
    draw — its fixture and package — and this harness; anything else is measured again (CMP-1-05,
    CMP-2-05)."""
    kept = state["measures"].get(name)
    art = state["artifacts"].get(name, {})
    draw = state["draw"] or {}
    if not kept or kept.get("artifact_digest") != art.get("artifact_digest"):
        return None
    path = runs / kept["results"] / "result.json"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(result, dict) or not _complete(result):
        return None
    same = {"artifact_digest": art.get("artifact_digest"), "fixture_digest": draw.get("fixture_digest"),
            "package": draw.get("package"), "draw": draw.get("id"), "harness": draw.get("harness")}
    return result if all(result.get(k) == v and v is not None for k, v in same.items()) else None


@route.serialized
def run(commit: str, *, seed: int | None = None, runs: pathlib.Path = route.RUNS) -> dict:
    inputs = route.harness_inputs(commit)
    built = build_missing(commit, runs)
    state = route.load(runs)
    standing = state["draw"]
    if standing is None or (standing.get("status") == "clean" and not standing.get("finished")):
        # a new draw, or one an interruption left unfinished, carried on over its fixture (CMP-2-01)
        measured.run(commit, seed if seed is not None else secrets.randbelow(2**31), runs=runs)
        state = route.load(runs)
    draw = state["draw"]
    report = {"commit": commit, "built": built, "draw": {k: v for k, v in draw.items() if k not in ("package", "mutant_package")}}
    out = runs / "draws" / draw["id"] / "results"
    results = {}
    if draw["status"] == "clean":
        for name in measured.CANDIDATES:
            art = state["artifacts"].get(name, {})
            if "artifact_archive" not in art:
                # An assembly refused by form has no artifact: its verdict says so, and nothing is measured (CMP-1-05).
                results[name] = {"not_measured": f"no artifact: assembly {art.get('assembly', {}).get('class')}"}
                continue
            kept = _kept(state, name, runs)
            if kept is not None:
                results[name] = kept
                continue
            try:
                results[name] = measure_candidate(name, draw, state["artifacts"], out / name, runs)
            except route.Refused:
                raise
            except Exception as error:  # noqa: BLE001 — one candidate's failure leaves the other's results (CMP-2-05)
                results[name] = {"not_measured": f"failed: {type(error).__name__}: {error}"[:2000]}
                continue  # no pointer: the next invocation measures it again
            route.still(commit, inputs)  # nothing measured under a harness edited meanwhile is published (CMP-2-02)
            # The result first, then the pointer to it: an interruption between them leaves no pointer.
            (out / name / "result.json").write_text(json.dumps(results[name], indent=1, ensure_ascii=False, default=str) + "\n",
                                                    encoding="utf-8")
            state = route.load(runs)
            state["measures"][name] = {"artifact_digest": results[name]["artifact_digest"], "results": str((out / name).relative_to(runs))}
            route.save(state, runs)
    final = route.load(runs)
    report["verdicts"] = measured.verdicts(final)
    report["results"] = {n: (r if "not_measured" in r else {"result": str((out / n / "result.json").relative_to(runs)),
                                                            "check_passed": r["check"].get("passed")})
                         for n, r in results.items()}
    report["history"] = [{"harness": h_["harness"], "closed": h_["closed"], "records": [r["id"] for r in h_["records"]],
                          "verdicts": measured.verdicts({**final, "records": h_["records"]})} for h_ in final["history"]]
    report["artifacts"] = {n: {k: v for k, v in a.items() if k not in ("builder_inspection", "artifact_inspection")}
                           for n, a in final["artifacts"].items()}
    route.still(commit, inputs)
    out.mkdir(parents=True, exist_ok=True)
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
