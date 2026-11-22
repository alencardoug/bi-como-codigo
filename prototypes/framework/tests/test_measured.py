"""Step 4 of §7 (docs/framework_prototype.md §2.1, §2.2): the draw once
against the builder outputs at the harness they were built at, the measured
fixture and its G mutant sealed under `clear/measured/`, and each candidate's
run carried through assembly, `verify` and both inspections as a resume bound
to the fixture. A draw stands until a build or a harness change discards it."""

from __future__ import annotations

import json
import shutil

import pytest

import fixture as fx_mod
import measured
import route
import sandbox as sb
import verdict as v

pytestmark = pytest.mark.skipif(not shutil.which("bwrap"), reason="bubblewrap is not installed")
HEAD = route._git("rev-parse", "HEAD")
PASSED = lambda: sb.Proof(True, {"probe": True}, {})  # noqa: E731


@pytest.fixture(scope="module")
def drawn(tmp_path_factory):
    runs = tmp_path_factory.mktemp("runs")
    route.build_own(HEAD, runs=runs, require_clean=False, prove=PASSED)
    out = measured.run(HEAD, 20261122, runs=runs, measured=runs / "m", candidates=("own",), require_clean=False, limit=20)
    return runs, out


def test_a_clean_draw_seals_the_fixture_and_carries_b_through_its_stages(drawn):
    runs, out = drawn
    assert out["status"] == "clean" and out["draws"] >= 1
    state = route.load(runs)
    last = route.records(state)[-1]
    assert last.kind == "resume" and last.draw_clean and last.fixture == out["fixture_digest"]
    assert last.stages["assembly"].cls == "PASS" and last.stages["verify"].cls == "PASS"
    assert last.stages["inspect_builder"] == v.Stage() and last.stages["inspect_artifact"] == v.Stage()
    assert measured.verdicts(state)["own"].startswith(v.PASSES)
    dumped = json.loads((runs / "m" / out["id"] / "cells.json").read_text())
    assert fx_mod.Fixture.load(dumped).digest() == out["fixture_digest"]
    assert state["artifacts"]["own-mutant"]["assembly"]["class"] == "PASS"
    mutant = fx_mod.Fixture.load(json.loads((runs / "m" / f"{out['id']}-mutant" / "cells.json").read_text()))
    assert mutant.mutant and mutant.digest() != out["fixture_digest"]


def test_a_standing_draw_is_never_drawn_again_and_a_build_discards_it(drawn):
    runs, _ = drawn
    with pytest.raises(route.Refused, match="a draw stands"):
        measured.run(HEAD, 1, runs=runs, measured=runs / "m", candidates=("own",), require_clean=False)
    route.build_own(HEAD, runs=runs, require_clean=False, prove=PASSED)  # byte-identical, and still a new build
    state = route.load(runs)
    assert state["draw"] is None and state["artifacts"] == {}
    again = measured.run(HEAD, 2, runs=runs, measured=runs / "m", candidates=("own",), require_clean=False, limit=20)
    assert again["status"] == "clean" and "draw" in route.load(runs)["discarded"][-1]["what"]


def test_the_draw_refuses_a_builder_output_of_another_harness(tmp_path):
    route.build_own(HEAD, runs=tmp_path, require_clean=False, prove=PASSED)
    state = route.load(tmp_path)
    state["builds"]["own"]["harness"] = {"prototypes/framework": "another"}
    route.save(state, tmp_path)
    with pytest.raises(route.Refused, match="another harness"):
        measured.run(HEAD, 1, runs=tmp_path, measured=tmp_path / "m", candidates=("own",), require_clean=False)
    with pytest.raises(route.Refused, match="no archived builder output of evidence"):
        state["builds"]["own"]["harness"] = state["harness"]
        route.save(state, tmp_path)
        measured.run(HEAD, 1, runs=tmp_path, measured=tmp_path / "m", require_clean=False)


def test_a_fixture_reads_back_as_it_was_drawn():
    fx, _ = fx_mod.generate(7)
    assert fx_mod.Fixture.load(json.loads(json.dumps(fx.dump()))) == fx


@pytest.mark.parametrize("ending", ["exhausted", "stopped"])
def test_a_draw_that_ends_with_no_fixture_stops_the_verdict_with_its_reason(tmp_path, monkeypatch, ending):
    """CMP-1-04: through the writer, each ending gives `stopped` with its own reason and no clean draw."""
    import calibrate

    def ends(*args, **kwargs):
        record = {"draws": 3, "rejections": [{"draw": 1}]}
        if ending == "exhausted":
            raise fx_mod.DrawExhausted(record)
        raise fx_mod.DrawStopped([{"file": "x.bin", "reason": "unreadable"}], record)

    monkeypatch.setattr(calibrate, "draw_against", ends)
    route.build_own(HEAD, runs=tmp_path, require_clean=False, prove=PASSED)
    out = measured.run(HEAD, 1, runs=tmp_path, measured=tmp_path / "m", candidates=("own",), require_clean=False)
    assert out["status"] == ending and "package" not in out
    verdict = measured.verdicts(route.load(tmp_path))["own"]
    assert verdict.startswith(v.STOPPED), verdict
    assert ("could not read" in verdict) == (ending == "stopped") and ("exhausted" in verdict) == (ending == "exhausted")
    with pytest.raises(route.Refused, match="a draw stands"):
        measured.run(HEAD, 1, runs=tmp_path, measured=tmp_path / "m", candidates=("own",), require_clean=False)
