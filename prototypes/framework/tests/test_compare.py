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
    assert compare._kept(state, "own", tmp_path) == {"artifact_digest": "a1"}


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
