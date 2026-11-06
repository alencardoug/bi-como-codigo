"""The release checker (docs/publishing_pipeline.md) on fixtures, with no
network: what each step accepts and refuses. The tests that need GitHub or
Firebase — T1 to T11 of §7 — run on the real pipeline, not here."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import shutil
import subprocess

import pytest

from bi_como_codigo import release as r

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of what build and verify read: release/ and site/."""
    for name in ("release", "site"):
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("node_modules"))
    return tmp_path


def built(repo: pathlib.Path) -> pathlib.Path:
    out = repo / "deploy"
    r.build(repo, out)
    return out


# --- §3, §4.2: build and verify ---------------------------------------------------


def test_build_copies_exactly_the_inclusion_list(repo):
    (repo / "site" / "notes.txt").write_text("not included")
    files = r.build(repo, repo / "deploy")
    assert "site/notes.txt" not in files
    assert sorted(p.relative_to(repo / "deploy").as_posix() for p in (repo / "deploy").rglob("*") if p.is_file()) == sorted(
        f[len("site/"):] for f in files
    )


def test_build_refuses_an_existing_directory(repo):
    (repo / "deploy").mkdir()
    with pytest.raises(r.Refused, match="built fresh"):
        r.build(repo, repo / "deploy")


def test_build_refuses_a_symbolic_link(repo):
    (repo / "site" / "link.html").symlink_to(repo / "site" / "index.html")
    with pytest.raises(r.Refused, match="symbolic link"):
        r.build(repo, repo / "deploy")


def test_the_committed_fixture_verifies(repo):
    body = r.verify(repo, built(repo))
    assert {f["path"] for f in body["files"]} >= {"index.html", "package/manifest.json"}
    assert body["digest"] == r.canonical_digest([(f["path"], f["sha256"]) for f in body["files"]])


@pytest.mark.parametrize(
    "plant, reason",
    [
        (lambda d: (d / "releases.md").write_bytes(b"PAR1....PAR1"), "Parquet magic"),
        (lambda d: (d / "index.html").write_bytes(b"<p>BICP\x01</p>"), "clear payload"),
        (lambda d: (d / "extra.html").write_text("<p>hi</p>"), "inclusion list"),
        (lambda d: (d / "index.html").write_text("//# sourceMappingURL=x.map"), "source map"),
    ],
    ids=["planted_parquet", "planted_payload", "outside_inclusion", "source_map"],
)
def test_verify_refuses_what_must_not_reach_hosting(repo, plant, reason):
    """T6's planted clear file, and the inspection by content of PLAN §3.4."""
    deploy = built(repo)
    plant(deploy)
    with pytest.raises(r.Refused, match=reason):
        r.verify(repo, deploy)


def test_verify_refuses_a_tampered_manifest(repo):
    """T6: one envelope's sha256 wrong in the manifest."""
    deploy = built(repo)
    path = deploy / "package" / "manifest.json"
    manifest = json.loads(path.read_text())
    sha = manifest["reports"][0]["sha256"]
    manifest["reports"][0]["sha256"] = ("0" if sha[0] != "0" else "1") + sha[1:]
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    with pytest.raises(r.Refused, match="package"):
        r.verify(repo, deploy)


def test_verify_refuses_a_data_key_in_the_clear(repo):
    deploy = built(repo)
    manifest_raw = (deploy / "package" / "manifest.json").read_bytes()
    from bi_como_codigo import envelope as e

    manifest = e.validate_manifest(manifest_raw)
    envelopes = {p.name: p.read_bytes() for p in (deploy / "package").glob("*.bice")}
    dek = r._deks(manifest, envelopes, {p.id: p.password for p in r.profiles(repo)})[0]
    (deploy / "releases.md").write_text(f"key {dek.hex()}")
    with pytest.raises(r.Refused, match="data key"):
        r.verify(repo, deploy)


# --- §2, §4.1: the protected set ------------------------------------------------------


@pytest.mark.parametrize(
    "changed, hit",
    [
        ([".github/workflows/candidate.yml"], True),
        ([".github/workflows/new.yml"], True),
        (["firebase.json"], True),
        (["release/protected.txt"], True),
        (["src/bi_como_codigo/release.py"], True),
        (["site/index.html", "site/releases.md"], False),
        (["docs/publishing_pipeline.md"], False),
        (["firebase.json.bak"], False),
    ],
)
def test_touches_protected(changed, hit):
    assert bool(r.touches_protected(changed, r.protected())) is hit


# --- §4.4, condition 3: the authenticated record -------------------------------------


def run(i, path=".github/workflows/publish.yml", event="workflow_run", branch="main", conclusion="success", attempt=1):
    return {"id": i, "path": path, "event": event, "head_branch": branch, "conclusion": conclusion,
            "run_started_at": f"2026-11-06T0{i}:00:00Z", "run_attempt": attempt}


def record(head="h1", pr=7):
    return json.dumps({"pr": pr, "head_sha": head, "candidate_run": 99, "version": "v1", "channel": "pr-7",
                       "expires": "2026-12-01T00:00:00Z", "digest": "d"}).encode()


def lookup(runs, artifacts, head="h1"):
    return r.select_record(runs, head, lambda run_: artifacts.get(run_["id"], []), lambda a: a["body"])


@pytest.mark.parametrize("path", [".github/workflows/publish.yml", ".github/workflows/publish.yml@main",
                                  ".github/workflows/publish.yml@refs/heads/main"])
def test_record_found_by_the_publishers_path_bare_or_at_main(path):
    """PIPE-2-01: GitHub documents `path@ref`."""
    found = lookup([run(1, path=path)], {1: [{"id": 5, "name": "release-record", "body": record()}]})
    assert (found.version, found.artifact_id) == ("v1", 5)


@pytest.mark.parametrize(
    "bad",
    [
        {"path": ".github/workflows/candidate.yml"},
        {"path": ".github/workflows/publish.yml@refs/heads/pr"},
        {"path": ".github/workflows/publish.yml.bak"},
        {"event": "pull_request"},
        {"branch": "feature"},
        {"conclusion": "failure"},
    ],
    ids=["other_workflow", "other_ref", "lookalike_path", "pull_request_event", "other_branch", "failed"],
)
def test_record_of_a_run_that_is_not_the_publisher_on_main_is_ignored(bad):
    """T3's counterfeit: a PR's workflow can upload `release-record` to its own run."""
    with pytest.raises(r.Refused, match="no authenticated"):
        lookup([run(1, **bad)], {1: [{"id": 5, "name": "release-record", "body": record()}]})


def test_two_records_in_one_run_are_ambiguous():
    arts = [{"id": 5, "name": "release-record", "body": record()}, {"id": 6, "name": "release-record", "body": record()}]
    with pytest.raises(r.Refused, match="ambiguous"):
        lookup([run(1)], {1: arts})


def test_the_latest_run_for_the_head_is_taken_and_other_heads_skipped():
    runs = [run(1), run(2), run(3)]
    arts = {
        1: [{"id": 11, "name": "release-record", "body": record()}],
        2: [{"id": 12, "name": "release-record", "body": record()}],
        3: [{"id": 13, "name": "release-record", "body": record(head="other")}],
    }
    assert lookup(runs, arts).artifact_id == 12


# --- §4.5: the margin --------------------------------------------------------------


def test_margin_is_more_than_a_day():
    now = dt.datetime(2026, 11, 6, tzinfo=dt.timezone.utc)
    assert r.margin_ok("2026-11-07T00:00:01Z", now)
    assert not r.margin_ok("2026-11-07T00:00:00Z", now)
    assert not r.margin_ok("2026-11-06T12:00:00Z", now)


# --- §4.4, promote: T4b -----------------------------------------------------------------


def test_clone_takes_the_version_never_the_channel(monkeypatch):
    """T4b: the command against a stand-in CLI that records its arguments."""
    monkeypatch.setenv("FIREBASE_PROJECT", "proj")
    calls = []
    live = iter([None, {"release": {"version": {"name": "sites/s/versions/abc123"}}}])
    monkeypatch.setattr(r, "channel", lambda *_: next(live))
    outcome = r.promote("s", "abc123", "token", run=lambda cmd, check: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0))
    assert outcome == "promoted"
    assert calls == [["firebase", "hosting:clone", "s@abc123", "s:live", "--project", "proj"]]


def test_promote_fails_when_live_does_not_read_back_the_version(monkeypatch):
    live = iter([None, {"release": {"version": {"name": "sites/s/versions/other"}}}])
    monkeypatch.setattr(r, "channel", lambda *_: next(live))
    with pytest.raises(r.Refused, match="live serves other"):
        r.promote("s", "abc123", "token", run=lambda cmd, check: subprocess.CompletedProcess(cmd, 0))


def test_promote_does_nothing_when_live_already_serves_it(monkeypatch):
    monkeypatch.setattr(r, "channel", lambda *_: {"release": {"version": {"name": "sites/s/versions/abc123"}}})
    assert r.promote("s", "abc123", "token", run=lambda cmd, check: pytest.fail("cloned")) == "already live"


@pytest.mark.parametrize("version", ["", "pr-7:x", "s@v", "a b", "sites/s/versions/x"])
def test_clone_command_refuses_what_is_not_a_version_id(version):
    with pytest.raises(r.Refused):
        r.clone_command("s", version)


# --- §5: T8's binding oracle --------------------------------------------------------------

POOL = "projects/1/locations/global/workloadIdentityPools/github"


def policy(env):
    return {"bindings": [{"role": "roles/iam.workloadIdentityUser",
                          "members": [f"principalSet://iam.googleapis.com/{POOL}/attribute.environment/{env}"]}]}


def test_bindings_exactly_as_declared_pass():
    r.check_bindings({"pre": policy("preview"), "live": policy("production")}, POOL, {"pre": "preview", "live": "production"})


@pytest.mark.parametrize(
    "live_policy",
    [
        {"bindings": [{"role": "roles/iam.workloadIdentityUser", "members": [f"principalSet://iam.googleapis.com/{POOL}/*"]}]},
        policy("preview"),
        {"bindings": policy("production")["bindings"] + policy("preview")["bindings"]},
        {"bindings": []},
    ],
    ids=["pool_wide", "other_environment", "extra_member", "none"],
)
def test_bindings_refuse_anything_wider_or_other(live_policy):
    """PIPE-1-03: a pool-wide member, tried here on JSON, never in Google Cloud."""
    with pytest.raises(r.Refused):
        r.check_bindings({"pre": policy("preview"), "live": live_policy}, POOL, {"pre": "preview", "live": "production"})
