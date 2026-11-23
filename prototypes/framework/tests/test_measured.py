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


def _two(runs):
    """B built, and its build entered a second time as `evidence`: two candidates whose
    runs a test can interrupt, with no second framework to build."""
    route.build_own(HEAD, runs=runs, require_clean=False, prove=PASSED)
    state = route.load(runs)
    own = state["builds"]["own"]
    state["builds"]["evidence"] = {**own, "candidate": "evidence", "id": "evidence" + own["id"][3:]}
    run = next(r for r in state["records"] if r["id"] == own["id"])
    state["records"].append({**run, "id": "evidence" + own["id"][3:]})  # its build's record, as a real build leaves one
    route.save(state, runs)


def _finding_on_bs_artifact(real):
    import inspect_output as io_

    def inspect(root, needles, **kw):
        report = real(root, needles, **kw)
        if root.name == "artifact" and root.parent.name == "own":
            report.findings.append(io_.Finding(io_.INSPECT_NUMBER, "x.js", "x.js", "1"))
        return report
    return inspect


def test_an_interruption_keeps_a_judged_finding_and_the_run_carries_on(tmp_path, monkeypatch):
    """CMP-2-01: B's artifact inspected with a finding, then Evidence's inspection
    interrupted. The draw and every completed stage were in memory only, so the
    finding was lost; now they are kept as they complete, the interrupted stage
    recorded so, and the next invocation carries the run on over the same fixture."""
    import inspect_output as io_
    _two(tmp_path)
    real = io_.inspect_dir
    found = _finding_on_bs_artifact(real)

    def interrupted(root, needles, **kw):
        if root.name == "builder" and root.parent.name == "evidence":
            raise OSError("interrupted")
        return found(root, needles, **kw)

    monkeypatch.setattr(io_, "inspect_dir", interrupted)
    kw = dict(runs=tmp_path, measured=tmp_path / "m", require_clean=False, limit=20)
    with pytest.raises(OSError):
        measured.run(HEAD, 20261122, **kw)
    state = route.load(tmp_path)
    assert state["draw"] is not None and state["draw"]["status"] == "clean" and not state["draw"].get("finished")
    assert measured.verdicts(state)["own"].startswith(v.FAILS), measured.verdicts(state)
    ev = next(r for r in route.records(state) if r.id == f"{state['draw']['id']}-evidence")
    assert ev.stages["inspect_builder"].status == "interrupted"

    monkeypatch.setattr(io_, "inspect_dir", found)
    out = measured.run(HEAD, 1, **kw)  # carried on, not drawn again
    state = route.load(tmp_path)
    assert out["id"] == state["draw"]["id"] and state["draw"]["finished"]
    assert measured.verdicts(state)["own"].startswith(v.FAILS)  # the earlier finding still counts
    resumed = [r for r in route.records(state) if r.id.startswith(out["id"]) and r.id.endswith("-evidence")]
    assert len(resumed) == 2 and resumed[-1].stages["inspect_artifact"].status == "done"
    assert not any(r.id.endswith("-own") and "-r" in r.id[len(out["id"]):] for r in route.records(state))  # B was through
    assert state["artifacts"]["own-mutant"]["assembly"]["class"] == "PASS"
    with pytest.raises(route.Refused, match="a draw stands"):
        measured.run(HEAD, 1, **kw)


def test_an_interrupted_mutant_is_assembled_on_the_next_invocation(tmp_path, monkeypatch):
    """CMP-2-01: the mutant, a control, interrupted after both judged runs completed."""
    import harness as h
    route.build_own(HEAD, runs=tmp_path, require_clean=False, prove=PASSED)
    real = h.assemble

    def fails_on_the_mutant(builder, package_dir, *a, **k):
        if package_dir.parent.name.endswith("-mutant"):
            raise OSError("interrupted")
        return real(builder, package_dir, *a, **k)

    monkeypatch.setattr(h, "assemble", fails_on_the_mutant)
    kw = dict(runs=tmp_path, measured=tmp_path / "m", candidates=("own",), require_clean=False, limit=20)
    with pytest.raises(OSError):
        measured.run(HEAD, 20261122, **kw)
    state = route.load(tmp_path)
    assert measured.verdicts(state)["own"].startswith(v.PASSES)
    monkeypatch.setattr(h, "assemble", real)
    out = measured.run(HEAD, 1, **kw)
    state = route.load(tmp_path)
    assert state["draw"]["finished"] and state["artifacts"]["own-mutant"]["assembly"]["class"] == "PASS"
    assert len([r for r in state["records"] if r["id"].startswith(out["id"])]) == 1  # nothing of B carried again


def test_a_harness_changed_during_a_stage_is_never_recorded_under_the_first(tmp_path, monkeypatch):
    """CMP-2-02: a tracked input edited while a stage runs — here, the harness's
    identity changing during the builder output's inspection — leaves that stage
    interrupted, not done under the identity the run started with."""
    import inspect_output as io_
    route.build_own(HEAD, runs=tmp_path, require_clean=False, prove=PASSED)
    real_inputs, real_inspect = route.harness_inputs, io_.inspect_dir
    edited = {}

    def inputs(commit, **kw):
        now = real_inputs(commit, **kw)
        return {**now, "prototypes/framework/lists": "edited"} if edited else now

    def inspect(root, needles, **kw):
        edited["yes"] = True
        return real_inspect(root, needles, **kw)

    monkeypatch.setattr(route, "harness_inputs", inputs)
    monkeypatch.setattr(io_, "inspect_dir", inspect)
    with pytest.raises(route.Refused, match="harness changed during the run"):
        measured.run(HEAD, 20261122, runs=tmp_path, measured=tmp_path / "m", candidates=("own",), require_clean=False, limit=20)
    state = route.load(tmp_path)
    rec = next(r for r in route.records(state) if r.id == f"{state['draw']['id']}-own")
    assert rec.stages["inspect_builder"].status == "interrupted" and "assembly" not in rec.stages
    assert not measured.verdicts(state)["own"].startswith(v.PASSES)



# --- CMP-3-01, CMP-3-02: a resume keeps its draw, retries an error, assembles the archived seal ---


def test_a_clean_draw_after_an_exhausted_one_still_closes_it_when_its_inspection_is_resumed(tmp_path, monkeypatch):
    """CMP-3-01: an exhausted draw; B alone built again, which discards it; a clean draw whose
    Evidence inspection is interrupted, and its retry. The retry's record holds the clean draw,
    so the earlier exhaustion is closed."""
    import calibrate
    import inspect_output as io_
    _two(tmp_path)
    kw = dict(runs=tmp_path, measured=tmp_path / "m", require_clean=False, limit=20)
    real_draw = calibrate.draw_against

    def exhausted(*a, **k):
        raise fx_mod.DrawExhausted({"draws": 3, "rejections": []})
    monkeypatch.setattr(calibrate, "draw_against", exhausted)
    measured.run(HEAD, 1, **kw)
    monkeypatch.setattr(calibrate, "draw_against", real_draw)
    state = route.load(tmp_path)
    evidence = state["builds"]["evidence"]
    route.build_own(HEAD, runs=tmp_path, require_clean=False, prove=PASSED)  # B alone: the draw is discarded
    state = route.load(tmp_path)
    state["builds"]["evidence"] = evidence
    route.save(state, tmp_path)
    real = io_.inspect_dir

    def interrupted(root, needles, **k):
        if root.name == "builder" and root.parent.name == "evidence":
            raise OSError("interrupted")
        return real(root, needles, **k)
    monkeypatch.setattr(io_, "inspect_dir", interrupted)
    with pytest.raises(OSError):
        measured.run(HEAD, 20261122, **kw)
    monkeypatch.setattr(io_, "inspect_dir", real)
    measured.run(HEAD, 1, **kw)
    verdicts = measured.verdicts(route.load(tmp_path))
    # B's output under Evidence's lists is a cost by form; what matters is that the exhaustion is closed
    assert not verdicts["evidence"].startswith(v.STOPPED) and "exhausted" not in verdicts["evidence"], verdicts


def test_a_harness_error_is_retried_and_the_draw_stays_open_until_it_is_through(tmp_path, monkeypatch):
    """CMP-3-01: an assembly that returns HARNESS_ERROR left the draw finished and its run
    stopped for good; the draw now stays open, and the next invocation assembles again."""
    import harness as h
    route.build_own(HEAD, runs=tmp_path, require_clean=False, prove=PASSED)
    real = h.assemble
    calls = {"n": 0}

    def errs_once(builder, package_dir, *a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return h.Outcome("assembly", h.HARNESS_ERROR, "a transient error"), None
        return real(builder, package_dir, *a, **k)
    monkeypatch.setattr(h, "assemble", errs_once)
    kw = dict(runs=tmp_path, measured=tmp_path / "m", candidates=("own",), require_clean=False, limit=20)
    out = measured.run(HEAD, 20261122, **kw)
    assert not out.get("finished") and out["open"] == ["own"]
    again = measured.run(HEAD, 1, **kw)
    state = route.load(tmp_path)
    assert again["id"] == out["id"] and again["finished"] and measured.verdicts(state)["own"].startswith(v.PASSES)


def test_a_resume_assembles_the_archived_seal_never_a_new_one(tmp_path, monkeypatch):
    """CMP-3-02: B assembled, Evidence's assembly interrupted, the same cells sealed again
    beside the draw — another valid package —; the retry assembles Evidence from the draw's
    archived seal, and works with the expanded copy gone."""
    import harness as h
    _two(tmp_path)
    real = h.assemble
    seen = []

    def interrupted(builder, package_dir, *a, **k):
        seen.append(package_dir)
        if builder.parent.name == "evidence" and len(seen) == 2:
            raise OSError("interrupted")
        return real(builder, package_dir, *a, **k)
    monkeypatch.setattr(h, "assemble", interrupted)
    kw = dict(runs=tmp_path, measured=tmp_path / "m", require_clean=False, limit=20)
    with pytest.raises(OSError):
        measured.run(HEAD, 20261122, **kw)
    state = route.load(tmp_path)
    draw = state["draw"]
    folder = tmp_path / "m" / draw["id"]
    fx = fx_mod.Fixture.load(json.loads((folder / "cells.json").read_text()))
    shutil.rmtree(folder / "package")
    resealed = fx_mod.write(fx, tmp_path / "reseal")["package"]
    assert resealed != draw["package"]  # the same cells, another package
    shutil.copytree(tmp_path / "reseal" / "package", folder / "package")
    measured.run(HEAD, 1, **kw)
    state = route.load(tmp_path)
    import hashlib
    import trees
    for name in ("own", "evidence"):
        art = state["artifacts"][name]
        out = tmp_path / "x" / name
        trees.extract(tmp_path / art["artifact_archive"], out, art["artifact_digest"])
        held = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (out / h.PACKAGE).iterdir()}
        assert held == draw["package"], name
    shutil.rmtree(folder / "package")  # the expanded copy lost: the archived seal is enough
    assert measured._seal(state["draw"], "package", folder / "package", tmp_path / "y", tmp_path).is_dir()
