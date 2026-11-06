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
    return json.dumps({"pr": pr, "head_sha": head, "candidate_run": 99, "version": "v1", "channel": "pr-7", "url": "https://s--pr-7.web.app",
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


# --- round 1 of the implementation review ---------------------------------------------

import io
import zipfile


def zipped(entries: list[tuple[str, bytes, int | None]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data, mode in entries:
            info = zipfile.ZipInfo(name)
            if mode is not None:
                info.external_attr = mode << 16
            zf.writestr(info, data)
    return buf.getvalue()


@pytest.mark.parametrize(
    "name, mode",
    [("padding/../../trusted.py", None), ("../trusted.py", None), ("/etc/passwd", None), ("a\\..\\b", None),
     ("C:/x", None), ("./a", None), ("link", 0o120777)],
    ids=["internal_traversal", "leading_traversal", "absolute", "backslash", "drive", "dot", "symlink"],
)
def test_safe_extract_refuses_before_writing_anything(tmp_path, name, mode):
    """IMPL-1-01: the archive the pinned download action would have extracted unchecked."""
    archive = zipped([("deploy/index.html", b"ok", None), (name, b"PR code", mode)])
    with pytest.raises(r.Refused):
        r.safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "trusted.py").exists()


def test_safe_extract_refuses_a_repeated_entry(tmp_path):
    with pytest.raises(r.Refused, match="repeats"):
        r.safe_extract(zipped([("a.txt", b"1", None), ("a.txt", b"2", None)]), tmp_path / "out")


def test_safe_extract_keeps_both_artifact_layouts(tmp_path):
    archive = zipped([("deploy/package/manifest.json", b"{}", 0o100644), ("candidate.json", b"{}", None), ("deploy/", b"", 0o040755)])
    names = r.safe_extract(archive, tmp_path / "out")
    assert sorted(names) == ["candidate.json", "deploy/package/manifest.json"]
    assert (tmp_path / "out" / "deploy" / "package" / "manifest.json").read_bytes() == b"{}"


def fake_api(monkeypatch, pages: dict[str, object]):
    calls = []

    def answer(url, token):
        calls.append(url)
        for prefix, value in pages.items():
            if url.startswith(prefix):
                return value(url) if callable(value) else value
        raise AssertionError(url)

    monkeypatch.setattr(r, "_json", answer)
    return calls


def pr_files(n, protected_at=None):
    files = [{"filename": f"site/f{i}.html"} for i in range(n)]
    if protected_at is not None:
        files[protected_at] = {"filename": "release/protected.txt"}
    return files


def page_of(files):
    def get(url):
        import re

        page = int(re.search(r"[?&]page=(\d+)", url).group(1))
        return files[(page - 1) * 100 : page * 100]
    return get


API = "https://api.github.com/repos/o/r"
PULL = [{"number": 7, "state": "open", "head": {"sha": "h", "repo": {"full_name": "o/r"}}}]


@pytest.mark.parametrize(
    "changed_files, listed, reason",
    [(None, 5, "cannot all be listed"), (3000, 3000, "cannot all be listed"), (3001, 3000, "cannot all be listed"), (250, 200, "lists 200 of its 250")],
    ids=["count_absent", "at_cap", "over_cap", "truncated"],
)
def test_admit_refuses_a_file_list_it_cannot_prove_complete(monkeypatch, changed_files, listed, reason):
    """IMPL-1-02: the count from the PR's own detail, and the listed objects equal to it."""
    detail = {"number": 7} if changed_files is None else {"number": 7, "changed_files": changed_files}
    fake_api(monkeypatch, {f"{API}/commits/h/pulls": PULL, f"{API}/pulls/7/files": page_of(pr_files(listed)), f"{API}/pulls/7": detail})
    with pytest.raises(r.Refused, match=reason):
        r.admit("o/r", "o/r", "h", "t")


def test_admit_finds_a_protected_file_on_a_later_page(monkeypatch):
    fake_api(monkeypatch, {f"{API}/commits/h/pulls": PULL, f"{API}/pulls/7/files": page_of(pr_files(150, protected_at=140)), f"{API}/pulls/7": {"changed_files": 150}})
    with pytest.raises(r.Refused, match="protected set"):
        r.admit("o/r", "o/r", "h", "t")


def test_admit_counts_a_rename_once_and_checks_its_old_name(monkeypatch):
    files = [{"filename": "site/new.html", "previous_filename": "firebase.json"}, {"filename": "site/a.html"}]
    fake_api(monkeypatch, {f"{API}/commits/h/pulls": PULL, f"{API}/pulls/7/files": page_of(files), f"{API}/pulls/7": {"changed_files": 2}})
    with pytest.raises(r.Refused, match="firebase.json"):
        r.admit("o/r", "o/r", "h", "t")


def test_admit_accepts_an_ordinary_pr(monkeypatch):
    fake_api(monkeypatch, {f"{API}/commits/h/pulls": PULL, f"{API}/pulls/7/files": page_of(pr_files(3)), f"{API}/pulls/7": {"changed_files": 3}})
    assert r.admit("o/r", "o/r", "h", "t") == 7


def test_admit_refuses_a_fork():
    with pytest.raises(r.Refused, match="fork"):
        r.admit("o/r", "someone/r", "h", "t")


def test_paged_reads_every_page_and_refuses_an_endless_one(monkeypatch):
    fake_api(monkeypatch, {"u": page_of([{"i": i} for i in range(250)])})
    assert len(r._paged("u", "t")) == 250
    fake_api(monkeypatch, {"u": lambda url: [{}] * 100})
    with pytest.raises(r.Refused, match="pages"):
        r._paged("u", "t")


def test_verify_refuses_entitlements_other_than_the_declaration(repo):
    """IMPL-1-03: Logística widened to every report, re-encrypted consistently."""
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    import site_fixture
    from bi_como_codigo import envelope as e

    declared = r.profiles(repo)
    widened = [e.DeclaredProfile(p.id, p.label, p.password, ("P01", "P02", "P13")) for p in declared]
    manifest, files = e.encrypt_package(widened, site_fixture.payloads(declared))
    package = repo / "site" / "package"
    shutil.rmtree(package)
    package.mkdir()
    (package / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (package / name).write_bytes(data)
    with pytest.raises(r.Refused, match="entitlements"):
        r.verify(repo, built(repo))


def test_verify_refuses_a_data_key_in_uppercase_hex(repo):
    """IMPL-1-11."""
    deploy = built(repo)
    from bi_como_codigo import envelope as e

    manifest = e.validate_manifest((deploy / "package" / "manifest.json").read_bytes())
    envelopes = {p.name: p.read_bytes() for p in (deploy / "package").glob("*.bice")}
    dek = r._deks(manifest, envelopes, {p.id: p.password for p in r.profiles(repo)})[0]
    (deploy / "releases.md").write_text(dek.hex().upper())
    with pytest.raises(r.Refused, match="data key"):
        r.verify(repo, deploy)


def test_build_selects_exactly_what_the_globs_select(repo):
    """IMPL-1-09: an oracle apart from `included_files` — pathlib's own glob."""
    globs = r.inclusion(repo)
    expected = sorted({p.relative_to(repo).as_posix() for g in globs for p in repo.glob(g) if p.is_file()})
    (repo / "site" / "notes.txt").write_text("excluded")
    files = r.build(repo, repo / "deploy")
    assert files == expected
    for rel in expected:
        assert (repo / "deploy" / rel[len("site/"):]).read_bytes() == (repo / rel).read_bytes()
    assert not (repo / "deploy" / "notes.txt").exists()


def test_firebase_config_names_the_configured_site(repo, tmp_path):
    """IMPL-1-05: a site different from the project's."""
    shutil.copy(ROOT / "firebase.json", repo / "firebase.json")
    r.firebase_config(repo, "sandbox-site", tmp_path / "firebase.json")
    assert json.loads((tmp_path / "firebase.json").read_text())["hosting"]["site"] == "sandbox-site"


PROVIDER = {
    "state": "ACTIVE",
    "oidc": {"issuerUri": "https://token.actions.githubusercontent.com"},
    "attributeMapping": dict(r.REQUIRED_MAPPING),
    "attributeCondition": r.expected_condition("o/r", [".github/workflows/publish.yml", ".github/workflows/promote.yml"]),
}


def test_provider_exactly_as_declared_passes():
    r.check_provider(PROVIDER, "o/r", [".github/workflows/publish.yml", ".github/workflows/promote.yml"])


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(attributeCondition=p["attributeCondition"].replace("refs/heads/main'", "refs/heads/dev'", 1)),
        lambda p: p.update(attributeCondition=p["attributeCondition"].replace("promote.yml", "other.yml")),
        lambda p: p.update(attributeCondition=p["attributeCondition"].replace("'o/r'", "'x/r'")),
        lambda p: p.update(attributeCondition="true"),
        lambda p: p["attributeMapping"].pop("attribute.environment"),
        lambda p: p.update(state="DELETED"),
        lambda p: p.update(oidc={"issuerUri": "https://example.com"}),
    ],
    ids=["other_ref", "other_workflow", "other_repository", "permissive", "no_environment_mapping", "deleted", "other_issuer"],
)
def test_provider_refuses_any_widening(change):
    """IMPL-1-06: mutations tried on JSON, never in Google Cloud."""
    p = json.loads(json.dumps(PROVIDER))
    change(p)
    with pytest.raises(r.Refused):
        r.check_provider(p, "o/r", [".github/workflows/publish.yml", ".github/workflows/promote.yml"])


def test_check_channel_refuses_a_deleted_version(monkeypatch, capsys):
    """IMPL-1-10: the channel still names the version, but the version is gone."""
    monkeypatch.setattr(r, "channel", lambda *_: {"release": {"version": {"name": "sites/s/versions/v"}}, "expireTime": "2099-01-01T00:00:00Z"})
    monkeypatch.setattr(r, "_http", lambda url, *a, **k: (200, {}, json.dumps({"status": "DELETED"}).encode()))
    assert r.main(["check-channel", "--site", "s", "--channel", "pr-7", "--version", "v"]) == 1
    assert "DELETED" in capsys.readouterr().out


def test_download_drops_the_token_at_the_storage_redirect(monkeypatch):
    """IMPL-2-01: GitHub's token reaches GitHub only, never the signed storage URL."""
    import http.server
    import threading

    seen = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen[self.path] = self.headers.get("Authorization")
            if self.path == "/api":
                self.send_response(302)
                self.send_header("Location", f"https://127.0.0.1:{port}/blob")
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"zip")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    fetched = {}
    monkeypatch.setattr(r, "_http", lambda url, token=None, accept="": fetched.setdefault("call", (url, token)) and (200, {}, b"zip"))
    try:
        assert r._download(f"http://127.0.0.1:{port}/api", "secret-token") == b"zip"
    finally:
        server.shutdown()
    assert seen["/api"] == "Bearer secret-token"
    assert fetched["call"] == (f"https://127.0.0.1:{port}/blob", None)


def test_paged_refuses_a_listing_shorter_than_its_total(monkeypatch):
    """IMPL-2-02: 1,000 runs returned of 1,500."""
    def get(url, token):
        import re

        page = int(re.search(r"[?&]page=(\d+)", url).group(1))
        return {"total_count": 1500, "workflow_runs": [{}] * (100 if page <= 10 else 0)}

    monkeypatch.setattr(r, "_json", get)
    with pytest.raises(r.Refused, match="1000 of 1500"):
        r._paged("u", "t", "workflow_runs")
