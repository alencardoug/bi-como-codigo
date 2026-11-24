"""The world an exporter test runs in (docs/exporter.md §12): a temporary
repository with the trusted declarations migrated to the fixture's 16 reports
and an invented package of their shapes committed in `site/package/` — the
stand-in for live —, a staging root, a destination, and the environment.

It lives under a directory of `tempfile.mkdtemp`, not pytest's `tmp_path`,
whose parametrized names hold brackets the path rule of §10 refuses.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

from bi_como_codigo import contract as c, envelope as e, release
from bi_como_codigo.exporter import metadata as m, reference, views as V, writer as w

import fake_warehouse as fw

ROOT = pathlib.Path(__file__).resolve().parent.parent

PROFILES_ABOUT = "The one declaration of the showcase's profiles (PLAN §3.2, N22, N23). Both passwords are public by design and registered in docs/public_by_design.yml."
PASSWORDS = {"diretoria": "senha_complexa_123", "logistica": "complexa_senha_321"}  # docs/public_by_design.yml


def git(cwd: pathlib.Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@example.invalid"})
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, check=True, text=True, env=env).stdout


def profiles_json(reports: list[str]) -> bytes:
    body = {
        "about": PROFILES_ABOUT,
        "profiles": [
            {"id": "diretoria", "label": "Diretoria", "password": PASSWORDS["diretoria"], "reports": sorted(reports)},
            {"id": "logistica", "label": "Logística", "password": PASSWORDS["logistica"], "reports": ["P13"]},
        ],
    }
    return (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def payloads_from(views: V.ViewContract, contract: c.Contract, rows: dict[str, list[tuple]], run_dir: pathlib.Path):
    """The 16 payloads of the given rows, through the exporter's own freeze,
    totals and writer."""
    con = w.connect(run_dir)
    out = {}
    try:
        for view in views.views:
            report = contract.reports[view.report]
            frozen = reference.freeze(view, rows[view.view])
            path = w.write(con, run_dir, view, report, list(frozen.rows))
            out[view.report] = (reference.totals(contract, report, frozen), path.read_bytes())
    finally:
        con.close()
    return out


@dataclasses.dataclass
class World:
    base: pathlib.Path
    root: pathlib.Path
    staging: pathlib.Path
    out: pathlib.Path
    environ: dict[str, str]
    fixture: dict
    metadata_raw: bytes
    metadata_blob: str

    def fake(self) -> fw.Fake:
        return fw.Fake(self.fixture, (self.root / "release" / "views.json").read_bytes())

    def views_json(self) -> dict:
        return json.loads((self.root / "release" / "views.json").read_bytes())

    def write_views(self, body: dict, regenerate: bool = True) -> None:
        """A changed view contract, written as `export propose` lays it out,
        with the report contract regenerated unless a test says otherwise."""
        from bi_como_codigo.exporter import propose as P

        raw = P.dump(body)
        (self.root / "release" / "views.json").write_bytes(raw)
        if regenerate:
            (self.root / "release" / "contract.json").write_bytes(V.report_contract(V.load(raw)))

    def rewitness(self, fake: fw.Fake, view: str) -> None:
        """A mutation that changes a view's rows regenerates its witness (§12)."""
        body = self.views_json()
        v = fake.contract.by_view()[view]
        for build in body["accepted_builds"]:
            for entry in build["witness"]:
                if entry["view"] == view:
                    entry["rows"], entry["md5"] = len(fake.rows[view]), fw.fingerprint(v, fake.rows[view])
        self.write_views(body)

    def fetch_metadata(self, raw: bytes | None = None):
        data = self.metadata_raw if raw is None else raw

        def fetch(_checkout, contract):
            return m.check(data, self.metadata_blob, contract)

        return fetch

    def cleanup(self) -> None:
        shutil.rmtree(self.base, ignore_errors=True)


def copy_world(w: World) -> World:
    """A fresh copy of a built world, for one test: building one seals a package."""
    base = pathlib.Path(tempfile.mkdtemp(prefix="bice-test-"))
    shutil.rmtree(base)
    shutil.copytree(w.base, base, symlinks=True)
    environ = {k: (v.replace(str(w.base), str(base)) if v.startswith(str(w.base)) else v) for k, v in w.environ.items()}
    moved = {f.name: pathlib.Path(str(getattr(w, f.name)).replace(str(w.base), str(base))) for f in dataclasses.fields(w)
             if f.name in ("root", "staging", "out")}
    return World(base, moved["root"], moved["staging"], moved["out"], environ, w.fixture, w.metadata_raw, w.metadata_blob)


def make_world() -> World:
    base = pathlib.Path(tempfile.mkdtemp(prefix="bice-test-"))
    root = base / "repo"
    root.mkdir()
    for name in ("release", "site"):
        shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("node_modules", "firebase-tools"))
    fx = fw.load_fixture()
    views_raw = fw.contract_bytes(fx)
    views = V.load(views_raw)
    (root / "release" / "views.json").write_bytes(views_raw)
    (root / "release" / "contract.json").write_bytes(V.report_contract(views))
    (root / "release" / "profiles.json").write_bytes(profiles_json([v.report for v in views.views]))
    contract = c.load_contract(V.report_contract(views))
    scratch = base / "scratch"
    scratch.mkdir()
    rows = {v.view: fw.typed_rows(v, fx["rows"][v.view]) for v in views.views}
    declared = release.profiles(root)
    manifest, files = e.encrypt_package(declared, payloads_from(views, contract, rows, scratch))
    shutil.rmtree(scratch)
    package = root / "site" / "package"
    shutil.rmtree(package)
    package.mkdir()
    (package / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (package / name).write_bytes(data)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the migrated fixture")
    eng2 = base / "eng2"
    eng2.mkdir()
    staging = base / "staging"
    staging.mkdir()
    environ = {
        "BICE_WAREHOUSE_HOST": "127.0.0.1",
        "BICE_WAREHOUSE_PORT": "5432",
        "BICE_WAREHOUSE_DB": "warehouse",
        "BICE_WAREHOUSE_USER": "consumption_reader",
        "BICE_WAREHOUSE_PASSWORD": "invented-password-for-tests",
        "BICE_WAREHOUSE_SSLMODE": "prefer",
        "ENG_DADOS_2_DIR": str(eng2),
        "BICE_EXPORT_STAGING": str(staging),
        "BICE_EXPORT_DIR": str(base / "out"),
    }
    raw = fx["metadata"].encode("utf-8")
    return World(base, root, staging, base / "out", environ, fx, raw, views.metadata_blob)
