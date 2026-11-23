"""`make prototype`'s comparison (compare.py) on its ordinary failures (CMP-1-05):
an assembly refused by form gives a report, not an exception; what is measured
is the archived tree and the recorded fixture; a result is reused only when
its file exists and is of the artifact."""

from __future__ import annotations

import json

import pytest

import compare
import fixture as fx_mod
import route
import trees


def _clean_draw(tmp_path, monkeypatch, artifacts):
    state = route.load(tmp_path)
    state.update(draw={"id": "d1", "status": "clean", "fixture_digest": "f", "finished": "t"}, artifacts=artifacts)
    route.save(state, tmp_path)
    monkeypatch.setattr(compare, "build_missing", lambda commit, runs: [])
    monkeypatch.setattr(route, "harness_inputs", lambda commit, **kw: {"prototypes/framework": "h"})  # no commit to read


def test_an_assembly_refused_by_form_is_reported_not_raised(tmp_path, monkeypatch):
    form = {"assembly": {"class": "FORM", "message": "a manifest.json of its own"}, "artifact_digest": None}
    _clean_draw(tmp_path, monkeypatch, {"own": form, "evidence": form})
    report = compare.run("c", runs=tmp_path)
    assert report["results"] == {n: {"not_measured": "no artifact: assembly FORM"} for n in ("own", "evidence")}
    assert (tmp_path / "draws" / "d1" / "results" / "report.json").is_file()


def test_a_result_is_reused_only_from_its_file_and_its_artifact(tmp_path):
    state = route.load(tmp_path)
    state["artifacts"] = {"own": {"artifact_digest": "a1"}}
    state["measures"] = {"own": {"artifact_digest": "a1", "results": "draws/d1/results/own"}}
    assert compare._kept(state, "own", tmp_path) is None  # a pointer an interruption left with no result
    folder = tmp_path / "draws" / "d1" / "results" / "own"
    folder.mkdir(parents=True)
    (folder / "result.json").write_text(json.dumps({"artifact_digest": "a0"}))
    assert compare._kept(state, "own", tmp_path) is None  # a result of another artifact
    (folder / "result.json").write_text(json.dumps({"artifact_digest": "a1"}))
    assert compare._kept(state, "own", tmp_path) is None  # a result with no draw or harness to bind it (CMP-2-05)


def test_the_artifact_is_used_from_its_archive_and_the_fixture_by_its_digest(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.html").write_text("ok")
    digest = trees.archive(src, tmp_path / "a.tar.gz")
    assert (compare._bound(tmp_path, "a.tar.gz", digest, tmp_path / "x") / "index.html").read_text() == "ok"
    with pytest.raises(ValueError, match="is not the archive"):
        compare._bound(tmp_path, "a.tar.gz", "0" * 64, tmp_path / "y")
    fx, _ = fx_mod.generate(7)
    folder = tmp_path / "m" / "d1"
    folder.mkdir(parents=True)
    (folder / "cells.json").write_text(json.dumps(fx.dump()))
    monkeypatch.setattr(compare.measured, "MEASURED", tmp_path / "m")
    assert compare._fixture({"id": "d1"}, digest=fx.digest()) == fx
    with pytest.raises(route.Refused, match="is not the fixture"):
        compare._fixture({"id": "d1"}, digest="another")


# --- CMP-2-05 -----------------------------------------------------------------------------


def _measurable(tmp_path, monkeypatch, *, mutant_archive: bool):
    """A draw with B's artifact and builder archived, its fixture sealed; the measuring itself
    stubbed, recording what it was given."""
    import dataclasses as dc
    import harness as h
    fx, _ = fx_mod.generate(7)
    m = tmp_path / "m" / "d1"
    package = fx_mod.write(fx, m)["package"]
    (m / "cells.json").write_text(json.dumps(fx.dump()))
    builder = tmp_path / "b"
    builder.mkdir()
    (builder / "index.html").write_text("ok")
    art = tmp_path / "a"
    shutil_copy = __import__("shutil").copytree
    shutil_copy(builder, art)
    shutil_copy(m / "package", art / h.PACKAGE)
    runs = tmp_path / "runs"
    runs.mkdir()
    bd, ad = trees.archive(builder, runs / "b.tar.gz"), trees.archive(art, runs / "a.tar.gz")
    state = route.load(runs)
    state["builds"]["own"] = {"id": "own-1", "archive": "b.tar.gz", "builder_digest": bd}
    artifacts = {"own": {"artifact_archive": "a.tar.gz", "artifact_digest": ad},
                 "own-mutant": {"assembly": {"class": "FORM"}} if not mutant_archive else {}}
    draw = {"id": "d1", "fixture_digest": fx.digest(), "package": package, "harness": {"x": "h"}}
    state.update(draw=draw, artifacts=artifacts)
    route.save(state, runs)
    monkeypatch.setattr(compare.measured, "MEASURED", tmp_path / "m")
    given = {}

    @dc.dataclass
    class Diagnosis:
        def leads(self):
            return []
    monkeypatch.setattr(compare.check, "run", lambda name, a, fx, out, **kw: given.update(check=kw) or {"passed": False})
    monkeypatch.setattr(compare.builder_controls, "run", lambda name, b, d, pkg, fx, out, **kw: given.update(package=pkg) or [])
    monkeypatch.setattr(compare.diagnose, "run", lambda *a, **kw: Diagnosis())
    for f in ("run", "lines", "gate_lists", "dependencies", "build_measures", "upkeep"):
        monkeypatch.setattr(compare.measure, f, lambda *a, **kw: {})
    return runs, draw, artifacts, given


def test_a_refused_mutant_leaves_bs_results_with_the_proof_missing(tmp_path, monkeypatch):
    runs, draw, artifacts, given = _measurable(tmp_path, monkeypatch, mutant_archive=False)
    result = compare.measure_candidate("own", draw, artifacts, tmp_path / "out", runs)
    assert "FORM" in result["mutant_missing"] and given["check"] == {}  # checked, with no mutant proof to pass on


def test_the_controls_take_the_package_the_artifact_holds(tmp_path, monkeypatch):
    runs, draw, artifacts, given = _measurable(tmp_path, monkeypatch, mutant_archive=False)
    compare.measure_candidate("own", draw, artifacts, tmp_path / "out", runs)
    assert given["package"].parts[-3:] == ("bound", "artifact", "package")


@pytest.mark.parametrize("change", ["fixture_digest", "package", "draw", "harness", "malformed", "not a dict", "header only"])
def test_a_kept_result_of_another_draw_harness_or_unreadable_is_measured_again(tmp_path, change):
    state = route.load(tmp_path)
    draw = {"id": "d1", "fixture_digest": "f", "package": {"P01.bice": "p"}, "harness": {"x": "h"}}
    state.update(draw=draw, artifacts={"own": {"artifact_digest": "a1"}},
                 measures={"own": {"artifact_digest": "a1", "results": "draws/d1/results/own"}})
    good = {"artifact_digest": "a1", "fixture_digest": "f", "package": {"P01.bice": "p"}, "draw": "d1", "harness": {"x": "h"},
            "check": {"passed": True}, "controls": [], "diagnostic": {}, "measures": {}, "static": {}}
    folder = tmp_path / "draws" / "d1" / "results" / "own"
    folder.mkdir(parents=True)
    (folder / "result.json").write_text(json.dumps(good))
    assert compare._kept(state, "own", tmp_path) == good
    header = {k: good[k] for k in ("artifact_digest", "fixture_digest", "package", "draw", "harness")}  # CMP-3-06: no body
    bad = {"malformed": "{not json", "not a dict": "[1]", "header only": json.dumps(header)}.get(change) or json.dumps({**good, change: "other"})
    (folder / "result.json").write_text(bad)
    assert compare._kept(state, "own", tmp_path) is None


def test_one_candidates_failure_leaves_the_others_results_and_a_report(tmp_path, monkeypatch):
    """CMP-2-05: a failure while measuring B is reported as such, Evidence is still measured."""
    arts = {n: {"artifact_archive": f"{n}.tar.gz", "artifact_digest": f"{n}-a"} for n in ("own", "evidence")}
    _clean_draw(tmp_path, monkeypatch, arts)

    def measure(name, draw, artifacts, out, runs):
        if name == "own":
            raise RuntimeError("the browser crashed")
        out.mkdir(parents=True)
        return {"artifact_digest": artifacts[name]["artifact_digest"], "check": {"passed": True}}

    monkeypatch.setattr(compare, "measure_candidate", measure)
    report = compare.run("c", runs=tmp_path)
    assert report["results"]["own"] == {"not_measured": "failed: RuntimeError: the browser crashed"}
    assert report["results"]["evidence"]["check_passed"] is True
    assert "own" not in route.load(tmp_path)["measures"]  # no pointer: measured again next time


def test_a_mutant_that_does_not_bind_is_a_missing_proof_not_an_abort(tmp_path, monkeypatch):
    """CMP-3-06: B's mutant cells replaced by the canonical ones refuse their digest; B is
    checked with its proof missing, and the comparison goes on."""
    runs, draw, artifacts, given = _measurable(tmp_path, monkeypatch, mutant_archive=True)
    fx, _ = fx_mod.generate(7)
    folder = tmp_path / "m" / "d1-mutant"
    folder.mkdir()
    (folder / "cells.json").write_text(json.dumps(fx.dump()))  # the canonical cells under the mutant's name
    mutant_dir = tmp_path / "mut"
    mutant_dir.mkdir()
    (mutant_dir / "index.html").write_text("ok")
    artifacts["own-mutant"] = {"artifact_archive": "m.tar.gz", "artifact_digest": trees.archive(mutant_dir, runs / "m.tar.gz"),
                               "fixture_digest": fx_mod.mutant(fx).digest()}
    result = compare.measure_candidate("own", draw, artifacts, tmp_path / "out", runs)
    assert "does not bind" in result["mutant_missing"] and given["check"] == {}
