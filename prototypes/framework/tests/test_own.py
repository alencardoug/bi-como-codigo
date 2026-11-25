"""Candidate B, the own build (docs/framework_prototype.md §2.4, §4): its build
step, its pinned third-party bodies, the Arrow module its engine imports, and
its report runner."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import tarfile

import pytest

import cdn

HERE = pathlib.Path(__file__).resolve().parents[1]
OWN = HERE / "own"
ENVELOPE = HERE.parents[2] / "site" / "app" / "envelope.mjs"
DUCKDB_TARBALL = HERE / "runs" / "third_party" / "duckdb-wasm-1.32.0.tgz"
SOURCES = ("build.py", "index.html", "page.css", "page.mjs", "report.mjs", "arrow.mjs", "source.package.mjs",
           "source.clear.mjs", "p01.report.json", "cdn.json")


def _work(tmp_path: pathlib.Path, parquet: bytes | None = None) -> pathlib.Path:
    work = tmp_path / "work"
    work.mkdir(parents=True)
    for name in SOURCES:
        shutil.copy(OWN / name, work / name)
    shutil.copy(ENVELOPE, work / "envelope.mjs")
    if parquet is not None:
        (work / "data").mkdir()
        (work / "data" / "p01.parquet").write_bytes(parquet)
    return work


def _build(work: pathlib.Path, mode: str) -> subprocess.CompletedProcess:
    return subprocess.run(["/usr/bin/python3", "-I", "build.py", mode], cwd=work, capture_output=True, text=True)


def _sri(data: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


def _importmap(html: str) -> dict:
    return json.loads(re.search(r'<script type="importmap">\n(.*?)\n</script>', html, re.S).group(1))


def test_every_tracked_source_is_a_build_input():
    tracked = subprocess.run(["git", "-C", str(HERE), "ls-files", "own/"], capture_output=True, text=True, check=True).stdout.split()
    if tracked:  # before the first commit nothing is tracked
        assert sorted(pathlib.PurePosixPath(t).name for t in tracked) == sorted(SOURCES)


def test_the_encrypted_route_build_carries_the_reader_and_no_data(tmp_path):
    work = _work(tmp_path)
    done = _build(work, "package")
    assert done.returncode == 0, done.stderr
    out = work / "build"
    names = sorted(p.name for p in out.rglob("*") if p.is_file())
    assert not any(n.endswith(".parquet") for n in names) and not (out / "data").exists() and not (out / "package").exists()
    html = (out / "index.html").read_text()
    imap = _importmap(html)
    assert imap["imports"]["./source.mjs"].startswith("./source.package.")
    assert imap["imports"]["./envelope.mjs"].startswith("./envelope.")
    for specifier, url in imap["imports"].items():  # every module, own or pinned, has its integrity
        token = imap["integrity"][url]
        if url.startswith("./"):
            assert token == _sri((out / url[2:]).read_bytes()), specifier
    envelope = imap["imports"]["./envelope.mjs"][2:]
    assert (out / envelope).read_bytes() == ENVELOPE.read_bytes()  # the reader, unchanged
    entry = re.search(r'<script type="module" src="\./(page\.[0-9a-f]{16}\.mjs)" integrity="([^"]+)">', html)
    assert entry and entry.group(2) == _sri((out / entry.group(1)).read_bytes())
    assert "bice:pins" not in html and "bice:entry" not in html


def test_the_clear_build_puts_the_parquet_beside_the_page(tmp_path):
    work = _work(tmp_path, parquet=b"PAR1 clear PAR1")
    assert _build(work, "clear").returncode == 0
    out = work / "build"
    assert (out / "data" / "p01.parquet").read_bytes() == b"PAR1 clear PAR1"
    imap = _importmap((out / "index.html").read_text())
    assert imap["imports"]["./source.mjs"].startswith("./source.clear.") and "./envelope.mjs" not in imap["imports"]


def test_the_build_is_byte_for_byte_reproducible_and_never_reuses_an_output(tmp_path):
    outputs = []
    for i in range(2):
        work = _work(tmp_path / str(i))
        assert _build(work, "package").returncode == 0
        outputs.append({p.relative_to(work / "build").as_posix(): p.read_bytes() for p in (work / "build").rglob("*") if p.is_file()})
    assert outputs[0] == outputs[1]
    again = _build(work, "package")
    assert again.returncode != 0 and "build/ exists" in again.stderr


def test_the_pinned_scripts_and_the_engine_are_loaded_by_their_declared_url_and_integrity(tmp_path):
    work = _work(tmp_path)
    assert _build(work, "package").returncode == 0
    html = (work / "build" / "index.html").read_text()
    declared = json.loads((OWN / "cdn.json").read_text())["files"]
    for f in declared:
        assert re.fullmatch(r"[0-9a-f]{64}", f["sha256"])
        if f["role"] != "extension":
            assert f["url"] == cdn.url(f["package"], f["version"], f["file"])
        if f["role"] == "script":
            assert f'<script src="{f["url"]}" integrity="{f["integrity"]}" crossorigin="anonymous"></script>' in html
        if f["role"] == "module":
            assert _importmap(html)["integrity"][f["url"]] == f["integrity"]
    pins = next((work / "build").glob("pins.*.mjs")).read_text()
    for f in declared:
        assert (f["integrity"] in pins) == (f["role"] in ("fetch", "extension"))
    assert set(re.findall(r'https://[^"\s]+', html)) == {f["url"] for f in declared if f["role"] in ("script", "module")}


def test_the_parquet_extension_is_the_body_evidence_pins_and_comes_only_from_duckdb(tmp_path):
    ext = [f for f in json.loads((OWN / "cdn.json").read_text())["files"] if f["role"] == "extension"]
    evidence = json.loads((HERE / "evidence" / "extensions.json").read_text())["files"]
    assert [(f["extension"], f["url"], f["sha256"]) for f in ext] == [("parquet", e["url"], e["sha256"]) for e in evidence]
    work = _work(tmp_path)
    decl = json.loads((work / "cdn.json").read_text())
    next(f for f in decl["files"] if f["role"] == "extension")["url"] = "https://cdn.jsdelivr.net/npm/x@1/parquet.duckdb_extension.wasm"
    (work / "cdn.json").write_text(json.dumps(decl))
    done = _build(work, "package")
    assert done.returncode != 0 and "not pinned on https://extensions.duckdb.org/" in done.stderr


def test_the_page_turns_autoloading_off_and_loads_the_pinned_extension():
    page = (OWN / "page.mjs").read_text()
    assert "SET GLOBAL autoinstall_known_extensions = false" in page and "SET GLOBAL autoload_known_extensions = false" in page
    assert page.index("autoload_known_extensions = false") < page.index("LOAD '${url}#/${pin.extension}.duckdb_extension.wasm'")


def test_a_declaration_with_an_unpinned_file_is_refused(tmp_path):
    work = _work(tmp_path)
    decl = json.loads((work / "cdn.json").read_text())
    del decl["files"][0]["integrity"]
    (work / "cdn.json").write_text(json.dumps(decl))
    done = _build(work, "package")
    assert done.returncode != 0 and "not pinned" in done.stderr


@pytest.mark.skipif(not DUCKDB_TARBALL.is_file(), reason="make prototype-third-party fetches DuckDB-WASM's tarball")
def test_the_arrow_module_exports_what_the_pinned_engine_reads_from_it():
    bundle = cdn.from_tarball(DUCKDB_TARBALL, "dist/duckdb-browser.mjs").decode()
    aliases = re.findall(r'import\*as ([A-Za-z_$][\w$]*) from"apache-arrow"', bundle)
    assert aliases and not re.search(r'from"(?!apache-arrow")[^".][^"]*"', bundle)  # apache-arrow is its only bare import
    read = {m for a in aliases for m in re.findall(rf"\b{re.escape(a)}\.([A-Za-z_$][\w$]*)", bundle)} - {"ts"}
    exported = set(re.search(r"export const \{([^}]*)\}", (OWN / "arrow.mjs").read_text()).group(1).replace(" ", "").split(","))
    assert read and read <= exported


def _tarball(files: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(f"package/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return out.getvalue()


def _registry(tarball: bytes):
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(tarball).digest()).decode()

    def get(url: str) -> bytes:
        if url.endswith(".tgz"):
            return tarball
        return json.dumps({"dist": {"tarball": "https://registry.npmjs.org/p/-/p-1.0.0.tgz", "integrity": integrity}}).encode()
    return get


def test_cdn_take_pins_the_tarball_file_and_refuses_another_body(tmp_path):
    body = b"export const x = 1;\n"
    decl = tmp_path / "cdn.json"
    decl.write_text(json.dumps({"files": [{"name": "p", "role": "module", "specifier": "p", "package": "p", "version": "1.0.0", "file": "x.mjs"}]}))
    taken = cdn.take(decl, tarballs=tmp_path / "tp", get_registry=_registry(_tarball({"x.mjs": body})), get_cdn=lambda url: body)
    f = taken["files"][0]
    assert f["url"] == "https://cdn.jsdelivr.net/npm/p@1.0.0/x.mjs" and f["sha256"] == hashlib.sha256(body).hexdigest()
    assert f["integrity"] == _sri(body) and json.loads(decl.read_text()) == taken
    assert cdn.check(decl, get_cdn=lambda url: body) == []
    assert cdn.check(decl, get_cdn=lambda url: body + b" ") == [f["url"]]
    (tmp_path / "tp").joinpath("p-1.0.0.tgz").unlink()
    ext = tmp_path / "ext.json"
    ext.write_text(json.dumps({"files": [{"name": "e", "role": "extension", "extension": "parquet", "url": "https://extensions.duckdb.org/v1/e.wasm"}]}))
    pinned = cdn.take(ext, get_cdn=lambda url: b"ext")["files"][0]
    assert pinned["sha256"] == hashlib.sha256(b"ext").hexdigest() and "package" not in pinned
    with pytest.raises(cdn.Refused, match="not the declared bytes"):
        cdn.take(ext, get_cdn=lambda url: b"other ext")
    with pytest.raises(cdn.Refused, match="not the npm tarball's file"):
        cdn.take(decl, tarballs=tmp_path / "tp", get_registry=_registry(_tarball({"x.mjs": body})), get_cdn=lambda url: b"other")


@pytest.mark.skipif(not shutil.which("node"), reason="Node is not installed")
def test_the_report_runner():
    done = subprocess.run(["node", "--test", str(HERE / "tests" / "own_report.test.mjs")], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-2000:]
