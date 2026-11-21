"""The allowlist of §2.2, the fetcher, and the offline install in the sandbox
(§5): data planted in a work folder refuses the phase, a tarball is checked
against the lockfile, and package code cannot reach a listener on the host's
loopback."""

from __future__ import annotations

import base64
import hashlib
import http.server
import io
import json
import shutil
import subprocess
import tarfile
import threading

import pytest

import allowlist as al
import npm_offline as npm
import sandbox as sb

HAVE_TOOLS = shutil.which("bwrap") and shutil.which("npm")


def _head() -> str:
    return subprocess.run(["git", "-C", str(al.REPO), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def _tarball(name="bice-probe-pkg", version="1.0.0", bin_script=True) -> bytes:
    files = {"package/package.json": json.dumps({"name": name, "version": version, **({"bin": {"bice-probe": "cli.js"}} if bin_script else {})}).encode(),
             "package/index.js": b"module.exports = 42;\n",
             "package/cli.js": b"#!/usr/bin/env node\nconsole.log(require('./index.js'));\n"}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, data in files.items():
            info = tarfile.TarInfo(path)
            info.size = len(data)
            info.mode = 0o755 if path.endswith("cli.js") else 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _integrity(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()


def _project(tmp_path, data: bytes, resolved: str | None = None):
    url = resolved or "https://registry.npmjs.org/bice-probe-pkg/-/bice-probe-pkg-1.0.0.tgz"
    project = tmp_path / "project"
    project.mkdir()
    (project / "package.json").write_text(json.dumps({"name": "p", "version": "1.0.0", "dependencies": {"bice-probe-pkg": "1.0.0"}}))
    lock = {"name": "p", "version": "1.0.0", "lockfileVersion": 3, "requires": True, "packages": {
        "": {"name": "p", "version": "1.0.0", "dependencies": {"bice-probe-pkg": "1.0.0"}},
        "node_modules/bice-probe-pkg": {"version": "1.0.0", "resolved": url, "integrity": _integrity(data), "bin": {"bice-probe": "cli.js"}}}}
    (project / "package-lock.json").write_text(json.dumps(lock))
    return project


# --- the allowlist -----------------------------------------------------------------------


def test_tracked_sources_come_from_the_commits_blobs(tmp_path):
    allow = al.tracked(_head(), "prototypes/framework/release/")
    assert {e.dest for e in allow.entries} == {"contract.json", "profiles.json", "public_values.json"}
    al.assemble(allow, tmp_path / "work")
    al.check(allow, tmp_path / "work")
    assert len(allow.digest) == 64


@pytest.mark.parametrize("plant", ["fixture/p01.parquet", "package/manifest.json", ".npm-cache/clear-mode-entry"])
def test_data_planted_in_a_work_folder_refuses_the_phase_naming_it(tmp_path, plant):
    allow = al.tracked(_head(), "prototypes/framework/release/")
    work = tmp_path / "work"
    al.assemble(allow, work)
    (work / plant).parent.mkdir(parents=True, exist_ok=True)
    (work / plant).write_bytes(b"PAR1 planted PAR1")
    with pytest.raises(al.Refused, match=plant.replace(".", r"\.")):
        al.check(allow, work)


def test_a_changed_or_missing_input_refuses_the_phase(tmp_path):
    allow = al.tracked(_head(), "prototypes/framework/release/")
    work = tmp_path / "work"
    al.assemble(allow, work)
    (work / "contract.json").write_text("{}")
    with pytest.raises(al.Refused, match="not the listed file"):
        al.check(allow, work)
    (work / "contract.json").unlink()
    with pytest.raises(al.Refused, match="listed and missing"):
        al.check(allow, work)


def test_a_link_leaving_the_folder_is_refused(tmp_path):
    root = tmp_path / "nm"
    root.mkdir()
    (root / "out").symlink_to("/etc/hostname")
    with pytest.raises(al.Refused, match="links outside"):
        al.files(root)


# --- the fetcher --------------------------------------------------------------------------


def test_the_lockfile_must_name_the_registry_and_an_integrity():
    good = {"lockfileVersion": 3, "packages": {"": {}, "node_modules/a": {"resolved": npm.REGISTRY + "a/-/a-1.tgz", "integrity": "sha512-x"},
                                               "node_modules/l": {"link": True}}}
    assert [n for n, _, _ in npm.entries(good)] == ["node_modules/a"]
    with pytest.raises(npm.Refused, match="outside"):
        npm.entries({"lockfileVersion": 3, "packages": {"node_modules/a": {"resolved": "https://evil.example/a.tgz", "integrity": "sha512-x"}}})
    with pytest.raises(npm.Refused, match="no integrity"):
        npm.entries({"lockfileVersion": 3, "packages": {"node_modules/a": {"resolved": npm.REGISTRY + "a.tgz"}}})


def test_a_tarball_is_checked_against_the_lockfile_and_cached(tmp_path):
    data = _tarball()
    project = _project(tmp_path, data)
    record = npm.fetch(project / "package-lock.json", tmp_path / "cache", get=lambda url: data)
    assert record["tarballs"][0]["sha256"] == hashlib.sha256(data).hexdigest()

    def no_network(url):
        raise AssertionError("a cached tarball is not fetched again")

    npm.fetch(project / "package-lock.json", tmp_path / "cache", get=no_network)
    with pytest.raises(npm.Refused, match="integrity"):
        npm.fetch(project / "package-lock.json", tmp_path / "other", get=lambda url: data + b"x")


# --- the offline install, in the sandbox -----------------------------------------------


@pytest.mark.skipif(not HAVE_TOOLS, reason="bubblewrap or npm is not installed")
def test_the_offline_install_runs_in_the_sandbox_from_the_harnesss_cache(tmp_path):
    data = _tarball()
    project = _project(tmp_path, data)
    record = npm.fetch(project / "package-lock.json", tmp_path / "cache", get=lambda url: data)
    allow = (al.single("package.json", project / "package.json") + al.single("package-lock.json", project / "package-lock.json")
             + npm.cache_allowlist(tmp_path / "cache", record))
    result = npm.install(allow, tmp_path / "work")
    assert result.returncode == 0, result.stderr.decode()[-2000:]
    modules = npm.keep_install(tmp_path / "work", tmp_path / "node_modules")
    assert any(e.dest == "node_modules/.bin/bice-probe" and e.sha256.startswith("symlink:") for e in modules.entries)
    build = al.single("package.json", project / "package.json") + modules
    al.assemble(build, tmp_path / "build")
    al.check(build, tmp_path / "build")
    ran = sb.run(tmp_path / "build", ["/usr/bin/sh", "-c", "./node_modules/.bin/bice-probe"])
    assert ran.stdout == b"42\n", ran.stderr


class _Serve(http.server.BaseHTTPRequestHandler):
    data = b""

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.data)))
        self.end_headers()
        self.wfile.write(self.data)

    def log_message(self, *args):
        pass


@pytest.fixture
def loopback_package():
    _Serve.data = _tarball()
    server = http.server.HTTPServer(("127.0.0.1", 0), _Serve)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/", _Serve.data
    server.shutdown()


@pytest.mark.skipif(not HAVE_TOOLS, reason="bubblewrap or npm is not installed")
def test_package_code_cannot_reach_a_listener_on_the_hosts_loopback(tmp_path, loopback_package):
    """§2.5.5, "No network for package code": an install with no tarball in the
    cache and a build that fetches, each against a package served on the
    loopback; through the real wrapper neither reaches it, and with the network
    shared both do."""
    registry, data = loopback_package
    url = f"{registry}bice-probe-pkg/-/bice-probe-pkg-1.0.0.tgz"
    project = _project(tmp_path, data, resolved=url)
    allow = al.single("package.json", project / "package.json") + al.single("package-lock.json", project / "package-lock.json")
    online_install = f"npm ci --registry={registry} --fetch-retries=0 --fetch-timeout=5000 --ignore-scripts --no-audit --no-fund --cache /work/.npm-cache"
    fetch_build = f"node -e \"fetch('{url}').then(r => r.arrayBuffer()).then(b => console.log(b.byteLength), () => process.exit(3))\""
    for name, script in (("install", online_install), ("build", fetch_build)):
        al.assemble(allow, tmp_path / f"{name}-closed")
        closed = sb.run(tmp_path / f"{name}-closed", ["/usr/bin/sh", "-c", script], timeout=120)
        assert closed.returncode != 0, name
        al.assemble(allow, tmp_path / f"{name}-open")
        shared = sb.run(tmp_path / f"{name}-open", ["/usr/bin/sh", "-c", script], options=sb.Options(unshare_net=False), timeout=120)
        assert shared.returncode == 0, (name, shared.stderr.decode()[-1500:])
