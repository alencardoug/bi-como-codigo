"""The export, end to end: the declarations before anything connects, the
metadata at the pin, the read in one transaction inside the private run
directory, the write and the round trip, the totals, the sealing, the private
candidate verified twice, and the result renamed into place with its receipt.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import time
from typing import Callable

from .. import contract as c
from .. import envelope as e
from .. import release
from . import CANDIDATE_REFUSED, SEAL_TAMPERED, Refused
from . import metadata as m
from . import paths, receipt as rc, reference, source as s, views as v, writer as w

TRUSTED = (
    "release/views.json",
    "release/contract.json",
    "release/profiles.json",
    "release/public_values.json",
    "release/include.txt",
    "release/media_types.txt",
)


@dataclasses.dataclass(frozen=True)
class Declarations:
    views: v.ViewContract
    contract: c.Contract
    profiles: list[e.DeclaredProfile]
    digests: dict[str, str]
    snapshot: dict[str, bytes]  # the trusted declarations' bytes, read once
    public_values: list[str]  # release/public_values.json's entries, in order


def declarations(root: pathlib.Path) -> Declarations:
    """§4.1 and §4.4, before connecting: the trusted declarations read **once**,
    as bytes — the strict view contract, the report contract equal to the
    generated one, and the profiles naming its reports. The candidate is built
    from these same bytes, so the receipt's digests are what `verify` judged
    (XIMPL-1-09)."""
    snapshot = {rel: (root / rel).read_bytes() for rel in TRUSTED}
    views = v.load(snapshot["release/views.json"])
    try:
        contract = v.check_generated(views, snapshot["release/contract.json"])
        data = json.loads(snapshot["release/profiles.json"].decode("utf-8"))
        declared = [e.DeclaredProfile(p["id"], p["label"], p["password"], tuple(p["reports"])) for p in data["profiles"]]
        c.declarations_agree(contract, {p.id: set(p.reports) for p in declared})
        c.load_public_values(snapshot["release/public_values.json"])
    except c.Refused as refusal:
        raise Refused(refusal.code, check="declarations") from None
    except (ValueError, KeyError, TypeError):
        raise Refused(c.CONTRACT_INVALID, check="declarations") from None
    public = [item["value"] for item in json.loads(snapshot["release/public_values.json"])["values"]]
    digests = {rel: hashlib.sha256(data).hexdigest() for rel, data in snapshot.items()}
    return Declarations(views, contract, declared, digests, snapshot, public)


class Clock:
    def __init__(self, now: Callable[[], float] = time.monotonic):
        self.now = now
        self.phases: dict[str, float] = {p: 0.0 for p in rc.PHASES}

    def add(self, phase: str, since: float) -> float:
        t = self.now()
        self.phases[phase] += t - since
        return t


def _git(root: pathlib.Path, *args: str) -> bytes:
    env = {k: val for k, val in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=env, check=False)
    if done.returncode != 0:
        raise Refused(CANDIDATE_REFUSED, check="git")
    return done.stdout


def rehearsed_commit(root: pathlib.Path) -> str:
    """The commit being rehearsed, resolved **once**: every read of it uses the
    full id, so a ref that moves meanwhile changes nothing (XIMPL-2-08)."""
    return _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()


def committed_paths(root: pathlib.Path, commit: str) -> set[str]:
    """Every regular file of `site/` at that commit — the names already public in Git."""
    out = set()
    for line in _git(root, "ls-tree", "-r", commit, "site/").decode("utf-8").splitlines():
        meta, _, rel = line.partition("\t")
        if meta.split()[0] in ("100644", "100755"):
            out.add(rel)
    return out


def _committed_package(root: pathlib.Path, commit: str) -> tuple[bytes, dict[str, bytes]]:
    """The stand-in for live (§10): `site/package/` at the commit being rehearsed."""
    names = _git(root, "ls-tree", "--name-only", commit, "site/package/").decode("utf-8").split()
    files = {pathlib.PurePosixPath(n).name: _git(root, "show", f"{commit}:{n}") for n in names if n.endswith(".bice")}
    return _git(root, "show", f"{commit}:site/package/manifest.json"), files


def _verify_code(refusal: release.Refused) -> str | None:
    """The first of the gate's own codes in `verify`'s reason; never the rest of it."""
    known = {val for name, val in vars(c).items() if name.isupper() and isinstance(val, str) and val.islower()}
    known |= {val for name, val in vars(e).items() if name.isupper() and isinstance(val, str) and val.islower()}
    for token in re.findall(r"[a-z_]+", str(refusal)):
        if token in known:
            return token
    return None


def candidate(root: pathlib.Path, run_dir: pathlib.Path, manifest: bytes, files: dict[str, bytes],
              snapshot: dict[str, bytes], public: list[str], searched: set[str]) -> dict:
    """§10, the private candidate: the working tree's `site/` with the real
    package, `release.build` as CI calls it, then `release.verify`, unchanged,
    with no live and with the committed package as the stand-in for live."""
    cand = run_dir / "candidate"
    shutil.copytree(root / "site", cand / "site", symlinks=True)
    (cand / "release").mkdir()
    for rel, data in snapshot.items():  # the declarations as read at the start, not as they are now
        (cand / rel).write_bytes(data)
    shutil.rmtree(cand / "site" / "package")
    (cand / "site" / "package").mkdir()
    (cand / "site" / "package" / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (cand / "site" / "package" / name).write_bytes(data)
    deploy = run_dir / "deploy"
    included = release.build(cand, deploy)
    listing = release.listing(deploy)
    commit = rehearsed_commit(root)
    public_names = committed_paths(root, commit)
    for rel in included:
        # XIMPL-2-01: the receipt and Git's evidence name the candidate's files, so every
        # name is one already public in Git, or one of the sealed package's own.
        if not rel.startswith("site/package/") and rel not in public_names:
            raise Refused(CANDIDATE_REFUSED, check="uncommitted_file")
    stand_in = _committed_package(root, commit)
    results = []
    for live_name, live in (("none", lambda: release.NO_LIVE), ("stand_in", lambda: stand_in)):
        try:
            record = release.verify(cand, deploy, live=live)
        except release.Refused as refusal:
            raise Refused(CANDIDATE_REFUSED, check=_verify_code(refusal) or live_name) from None
        if record["digest"] != release.canonical_digest(listing):
            raise Refused(CANDIDATE_REFUSED, check="listing")
        live_digest = "none" if live_name == "none" else hashlib.sha256(
            stand_in[0] + b"".join(stand_in[1][k] for k in sorted(stand_in[1]))).hexdigest()
        results.append({"live": live_digest, "passed": True})
    used = [i for i, value in enumerate(public) if value in searched]  # XIMPL-2-07: only what the gate would search
    return {
        "listing_digest": release.canonical_digest(listing),
        "files": [{"path": rel, "sha256": sha} for rel, sha in listing],
        "included": included,
        "verify": results,
        # By entry of release/public_values.json: those that exempted a value of
        # this package, and those that exempted none.
        "collisions_approved": {"used": used, "unused": [i for i in range(len(public)) if i not in used]},
    }


def export(
    root: pathlib.Path,
    environ: dict[str, str],
    *,
    connect: Callable[[s.Settings, pathlib.Path], s.Source] = s.connect,
    fetch_metadata: Callable[[pathlib.Path, v.ViewContract], m.Metadata] = m.fetch,
    now: Callable[[], float] = time.monotonic,
    diagnose: Callable | None = None,
):
    """The run (§3 to §10). Returns the receipt, already written with the
    sealed package and the metadata into `BICE_EXPORT_DIR`.

    With `diagnose`, the run stops once the payloads are checked: it returns
    `diagnose(contract, payloads, run_dir)`, seals nothing and writes no
    result — `export collisions` (§10, N108)."""
    clock = Clock(now)
    d = declarations(root)
    found = s.settings(environ)
    protected = paths.protected_roots(environ, root)
    staging = paths.staging_root(environ.get("BICE_EXPORT_STAGING"), protected)
    target = None
    if diagnose is None:
        destination = environ.get("BICE_EXPORT_DIR")
        target = paths.check(destination, protected) if destination else None
        if target is None:
            raise Refused(paths.PATH_REFUSED, check="BICE_EXPORT_DIR")
        if os.path.lexists(target):
            raise Refused(paths.PATH_EXISTS)
    checkout = environ.get("ENG_DADOS_2_DIR")
    if not checkout:
        raise Refused(s.ENVIRONMENT_INVALID, check="ENG_DADOS_2_DIR")
    meta = fetch_metadata(pathlib.Path(checkout), d.views)
    with paths.RunDirectory(staging, protected) as run_dir:
        t = clock.now()
        source = connect(found, run_dir / "absent")
        t = clock.add("connect", t)
        checks_time = [0.0]

        def freeze(view, rows):
            t0 = clock.now()
            try:
                return reference.freeze(view, rows)
            finally:
                checks_time[0] += clock.now() - t0

        try:
            read = s.read(source, d.views, freeze, clock=clock.now)
        finally:
            try:
                source.close()
            except Exception:
                pass
        t = clock.now()
        clock.phases["facts"] = read.timings["facts"]
        clock.phases["checks"] = checks_time[0]
        clock.phases["read"] = read.timings["read"] - checks_time[0]
        con = w.connect(run_dir)
        searched: set[str] = set()  # every value the gate's inspection searches for
        payloads: dict[str, tuple[bytes, bytes]] = {}
        retained: dict[str, str] = {}
        per_view = []
        try:
            for view in d.views.views:
                vr = read.views[view.view]
                report = d.contract.reports[view.report]
                totals = reference.totals(d.contract, report, vr.frozen)
                t0 = clock.now()
                written = w.write(con, run_dir, view, report, list(vr.frozen.rows))
                buffer, sha = w.retain(written)
                clock.add("write", t0)
                t0 = clock.now()
                staged = run_dir / f"{view.report}.read.parquet"
                w.stage(buffer, staged)
                back = w.read_back(con, view, report, staged)
                w.check_staged(staged, sha, view.view)
                reference.compare(vr.frozen, back)
                try:
                    checked = c.check_payload(d.contract, report, totals, buffer)
                    searched |= {x for x in checked.texts if len(x) >= 3}
                    searched |= {x for x in checked.numbers if c.eligible_number(x)}
                except c.Refused as refusal:
                    raise Refused(refusal.code, view.view, "gate") from None
                clock.add("read_back", t0)
                payloads[view.report] = hold(view, totals, buffer)
                retained[view.report] = sha
                per_view.append({
                    "view": view.view, "report": view.report, "rows": vr.rows, "fingerprint": vr.fingerprint,
                    "witness_equal": vr.witness_equal, "reference_digest": vr.frozen.digest, "parquet_sha256": sha,
                })
        finally:
            con.close()
        if diagnose is not None:
            return diagnose(d.contract, payloads, run_dir)
        t0 = clock.now()
        for report_id, (_totals, buffer) in payloads.items():
            if hashlib.sha256(buffer).hexdigest() != retained[report_id]:
                raise Refused(SEAL_TAMPERED, d.views.by_report()[report_id].view, "seal")
        manifest, files = seal(d.profiles, payloads)
        clock.add("seal", t0)
        t0 = clock.now()
        cand = candidate(root, run_dir, manifest, files, d.snapshot, d.public_values, searched)
        clock.add("candidate", t0)
        body = rc.build(
            views=d.views, metadata=meta, read=read, settings=found, per_view=per_view,
            envelopes=files, candidate=cand, declarations=d.digests, phases=clock.phases,
        )
        raw = rc.dump(body)
        rc.load(raw, d.views)  # read back strictly before anything leaves the run directory
        result = {"package/manifest.json": manifest, **{f"package/{n}": b for n, b in files.items()},
                  "metadata.json": meta.raw, "run.json": raw}
    # XIMPL-2-05: published only once the run directory is gone. A signal noted
    # during the cleaning is raised there, and nothing is published.
    paths.publish(str(target), result, protected)
    return body


def hold(view: v.View, totals: bytes, buffer: bytes) -> tuple[bytes, bytes]:
    """What the run keeps for sealing: the totals and the retained buffer, as
    they were read back. A seam for the tests' substitution (§12)."""
    return totals, buffer


def seal(profiles: list[e.DeclaredProfile], payloads: dict[str, tuple[bytes, bytes]]):
    """§9: `envelope.encrypt_package`, called as it is."""
    return e.encrypt_package(profiles, payloads)
