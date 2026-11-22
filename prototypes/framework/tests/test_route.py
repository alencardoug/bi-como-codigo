"""The encrypted route's build of Candidate B and the run's state (§2.2, §5,
§7 step 3): the build reads no data, runs in the proved sandbox, is archived
reproducibly, and every build invocation — a byte-identical one too — discards
the draw, both artifacts and every measure; so does a change of the harness."""

from __future__ import annotations

import json
import shutil

import pytest

import allowlist as al
import route
import sandbox as sb
import trees
import verdict as v

pytestmark = pytest.mark.skipif(not shutil.which("bwrap"), reason="bubblewrap is not installed")
HEAD = route._git("rev-parse", "HEAD")
PASSED = lambda: sb.Proof(True, {"probe": True}, {})  # noqa: E731


def _build(runs, **kwargs):
    return route.build_own(HEAD, runs=runs, require_clean=False, **{"prove": PASSED, **kwargs})


def test_b_encrypted_build_reads_no_data_and_is_archived(tmp_path):
    entry = route.build_own(HEAD, runs=tmp_path, require_clean=False)  # the real probe, through the real wrapper
    assert entry["status"] == "archived" and entry["sandbox_proof"]["passed"]
    listed = json.loads((tmp_path / "own" / entry["id"] / "allowlist.json").read_text())
    assert not any(e["dest"].endswith((".parquet", ".bice")) or e["dest"].startswith(("data/", "package/")) for e in listed)
    assert entry["build_input"] == route.own_allowlist(HEAD).digest
    out = tmp_path / "x"
    trees.extract(tmp_path / entry["archive"], out, entry["builder_digest"])
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert "index.html" in names and any(n.startswith("envelope.") for n in names) and not any(n.startswith(("data/", "package/")) for n in names)
    assert not (tmp_path / "own" / entry["id"] / "work").exists()
    state = route.load(tmp_path)
    assert state["builds"]["own"]["builder_digest"] == entry["builder_digest"]
    assert route.records(state)[-1].stages == {"build": v.Stage(), "archive": v.Stage()}


def test_any_build_discards_the_draw_artifacts_and_measures_even_a_byte_identical_one(tmp_path):
    first = _build(tmp_path)
    state = route.load(tmp_path)
    state.update(draw={"seed": 1}, artifacts={"own": "a"}, measures={"own": {"x": 1}})
    route.save(state, tmp_path)
    second = _build(tmp_path)
    assert second["builder_digest"] == first["builder_digest"] and second["id"] != first["id"]
    state = route.load(tmp_path)
    assert (state["draw"], state["artifacts"], state["measures"]) == (None, {}, {})
    assert state["discarded"][-1]["what"] == ["artifacts", "draw", "measures"] and second["id"] in state["discarded"][-1]["why"]
    assert [r.id for r in route.records(state)] == [first["id"], second["id"]]


def test_a_changed_harness_discards_them_too(tmp_path):
    state = route.load(tmp_path)
    route.enter_harness(state, {"prototypes/framework": "a"})
    state.update(draw={"seed": 1}, measures={"own": {}})
    route.enter_harness(state, {"prototypes/framework": "a"})
    assert state["draw"] == {"seed": 1}
    state["records"].append({"id": "r1"})
    route.enter_harness(state, {"prototypes/framework": "b"})
    assert state["draw"] is None and state["discarded"][-1]["why"] == "the harness inputs changed"
    assert state["records"] == [] and state["history"][-1]["records"] == [{"id": "r1"}]
    assert state["history"][-1]["harness"] == {"prototypes/framework": "a"}


def test_a_failed_probe_refuses_the_build_and_the_record_says_so(tmp_path):
    entry = _build(tmp_path, prove=lambda: sb.Proof(False, {"host loopback unreachable": False}, {}))
    assert entry["status"] == "sandbox probe failed" and "builder_digest" not in entry
    assert route.records(route.load(tmp_path))[-1].stages == {"build": v.Stage(status="error")}


def test_an_interrupted_build_is_recorded_before_it_runs(tmp_path):
    def interrupt():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _build(tmp_path, prove=interrupt)
    state = route.load(tmp_path)
    assert state["builds"]["own"]["status"] == "started"
    assert route.records(state)[-1].stages == {"build": v.Stage(status="interrupted")}


def test_the_harness_must_be_the_commit_it_names(tmp_path, monkeypatch):
    monkeypatch.setattr(route, "_git", lambda *a: " M prototypes/framework/route.py" if a[0] == "status" else "x")
    with pytest.raises(route.Refused, match="not .* as committed"):
        route.harness_inputs("x")


def test_a_build_that_fails_keeps_its_log_and_no_archive(tmp_path):
    entry = route.build("own", HEAD, route.own_allowlist(HEAD), ["/usr/bin/python3", "-I", "build.py", "nonsense"], "build",
                        runs=tmp_path, require_clean=False, prove=PASSED)
    assert entry["status"].startswith("build exited") and "archive" not in entry
    assert "unknown mode nonsense" in (tmp_path / "own" / entry["id"] / "build.log").read_text()


def test_data_planted_in_the_allowlist_is_refused_before_the_phase(tmp_path):
    work = tmp_path / "w"
    allow = route.own_allowlist(HEAD)
    al.assemble(allow, work)
    (work / "data").mkdir()
    (work / "data" / "p01.parquet").write_bytes(b"PAR1")
    with pytest.raises(al.Refused, match="data/p01.parquet is not in the allowlist"):
        al.check(allow, work)


def test_evidence_encrypted_sources_have_no_source_and_the_encrypted_page():
    if not route._git("ls-tree", "-r", "--name-only", HEAD, "--", "prototypes/framework/evidence/encrypted/"):
        pytest.skip("the encrypted page is not committed yet")
    dests = sorted(e.dest for e in route.evidence_sources(HEAD).entries)
    assert "pages/index.md" in dests and "components/Login.svelte" in dests and "components/envelope.mjs" in dests
    assert not any(d.startswith(("sources/", "encrypted/")) or d.endswith((".parquet", ".bice")) for d in dests)
    page = next(e for e in route.evidence_sources(HEAD).entries if e.dest == "pages/index.md")
    assert page.source.endswith(":prototypes/framework/evidence/encrypted/pages/index.md")
    envelope = next(e for e in route.evidence_sources(HEAD).entries if e.dest == "components/envelope.mjs")
    assert envelope.source.endswith(":web/envelope.mjs")
