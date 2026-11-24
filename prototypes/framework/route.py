"""The encrypted route's builds and the run's state (docs/framework_prototype.md
§2.2, §5, §7 step 3).

A build of the encrypted route reads its candidate's tracked sources at a
recorded commit and `web/envelope.mjs`, and nothing of any fixture: its work
folder is assembled fresh from an allowlist — archived with the build —,
checked before the phase, and the phase runs in the sandbox with no network,
after the sandbox's probe has passed through the same wrapper. The builder
output is copied out by the harness and archived reproducibly; its digest is
the builder output's identity.

The run's state is one file, `runs/state.json`, ignored by Git, keyed by
identities (§5, FPROTO-6-07): each build invocation's own id and build input —
the allowlist's digest —, the builder output's digest, and the harness inputs
— the Git trees of `prototypes/framework/` (declarations, `cdn.json`,
lockfiles and the sandbox wrapper among them) and of the gate's package, and
`web/envelope.mjs`. **Any** build invocation of either candidate discards the
draw, both artifacts and every measure, even when it reproduces the same
bytes; so does a change of the harness inputs. Every stage run is appended as
a `verdict.Record`.

    uv run --frozen --group prototype python prototypes/framework/route.py own --commit <sha>
    uv run --frozen --group prototype python prototypes/framework/route.py evidence --commit <sha>
"""

from __future__ import annotations

import contextlib
import dataclasses
import fcntl
import functools
import io
import json
import os
import pathlib
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import allowlist as al
import npm_offline as npm
import roots
import sandbox as sb
import trees
import verdict as v

HERE = pathlib.Path(__file__).resolve().parent
REPO = roots.CHECKOUT  # the repository: its Git objects; a snapshot's files are under HERE (CMP-3-03)
RUNS = roots.RUNS
#: What the harness is made of, by path in the repository, at a commit (§5) — the Python
#: dependencies too, which the inspector, the oracle and the compressors run on (CMP-1-03).
HARNESS_PATHS = ("prototypes/framework", "src/bi_como_codigo", "web/envelope.mjs", "pyproject.toml", "uv.lock", "firebase.json")
OWN_BUILD = ["/usr/bin/python3", "-I", "build.py", "package"]
#: Evidence's encrypted build: A7's configuration, and no `evidence sources` — there is no source (§3, A3).
EVIDENCE_BUILD = ["/usr/bin/sh", "-c", "npm run build:pinned"]
EVIDENCE_ENV = {"HOME": f"{sb.WORK}/.home", "EVIDENCE_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1", "NODE_OPTIONS": "--max-old-space-size=4096"}


class Refused(Exception):
    pass


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout.strip()


def harness_inputs(commit: str, *, require_clean: bool = True) -> dict[str, str]:
    """The Git object of each harness path at `commit`: the harness's identity (§5).

    Run from a snapshot of the commit (`pinned`), nothing of the working tree is
    read, and the objects are all there is to it. Run from the working tree, it
    must hold those objects: a tracked change or an untracked file under those
    paths refuses the run, and so does a HEAD whose harness objects are not the
    commit's — another commit with the same objects, a change of documents only,
    is the same harness (CMP-3-03)."""
    objects = {path: _git("rev-parse", f"{commit}:{path}") for path in HARNESS_PATHS}
    if require_clean and not roots.PINNED:
        dirty = _git("status", "--porcelain", "--untracked-files=all", "--", *HARNESS_PATHS)
        head = {path: _git("rev-parse", f"HEAD:{path}") for path in HARNESS_PATHS}
        if dirty or head != objects:
            raise Refused(f"the harness is not {commit} as committed:\n{dirty or 'HEAD holds other harness objects'}")
    return objects


def snapshot(commit: str, dest: pathlib.Path) -> pathlib.Path:
    """Every harness path's tracked files at `commit`, from its Git objects, into `dest`, read-only."""
    import tarfile
    data = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", commit, "--", *HARNESS_PATHS],
                          check=True, capture_output=True).stdout
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")
    for p in sorted(dest.rglob("*"), reverse=True):
        p.chmod(p.stat().st_mode & ~0o222)
    return dest


def _writable(root: pathlib.Path) -> None:
    for p in [root, *root.rglob("*")]:
        if not p.is_symlink():
            p.chmod(p.stat().st_mode | 0o200)


#: What the running interpreter's environment is synced from.
ENVIRONMENT = ("pyproject.toml", "uv.lock")


def _live_blob(path: str) -> str:
    """The Git object the working tree's file would be."""
    return _git("hash-object", "--", path)


def pinned(commit: str, script: str, argv: list[str]) -> None:
    """Run `script` again from a snapshot of `commit` — its code, lists, declarations and
    drivers exported from Git, read-only —, with the repository, the runs and the clear
    mode named by the environment: an edit of the working tree during a run, restored or
    not, reaches nothing the run reads (CMP-3-03). Inside a snapshot, nothing to do."""
    if roots.PINNED:
        return
    # The interpreter is this process's, whose environment `uv run --frozen` synced from the working
    # tree's lock: it runs the snapshot only when that lock and its project are the commit's (CMP-4-02).
    for path in ENVIRONMENT:
        if _live_blob(path) != _git("rev-parse", f"{commit}:{path}"):
            raise Refused(f"the environment is not {commit}'s: its {path} differs; sync it from the commit's lock first")
    base = RUNS / "harness"
    base.mkdir(parents=True, exist_ok=True)
    for old in base.iterdir():  # snapshots of earlier invocations, a day old or more
        if time.time() - old.stat().st_mtime > 86400:
            _writable(old)
            shutil.rmtree(old)
    dest = snapshot(commit, base / f"{commit[:12]}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(3)}")
    env = {**os.environ, "BICE_SNAPSHOT": "1", "BICE_REPO": str(REPO), "BICE_RUNS": str(RUNS), "BICE_CLEAR": str(roots.CLEAR),
           "PYTHONPATH": os.pathsep.join([str(dest / "src"), *filter(None, [os.environ.get("PYTHONPATH")])])}
    target = dest / "prototypes" / "framework" / script
    os.execve(sys.executable, [sys.executable, str(target), *argv], env)


def still(commit: str, inputs: dict[str, str], *, require_clean: bool = True) -> None:
    """The harness that runs is still `inputs`, as committed: checked again
    before a stage's outcome is recorded and before a result is published, so
    that a tracked file edited during a long run — a list, a declaration, a
    script read when its stage runs — is never judged under the identity the
    run started with (CMP-2-02). Refused otherwise; the stage stays as it was
    recorded before it ran, interrupted."""
    now = harness_inputs(commit, require_clean=require_clean)
    if now != inputs:
        raise Refused(f"the harness changed during the run: {sorted(k for k in inputs if now.get(k) != inputs[k])}")


# --- the state ------------------------------------------------------------------------------

def _empty() -> dict:
    return {"harness": None, "builds": {}, "draw": None, "artifacts": {}, "measures": {}, "records": [], "discarded": [],
            "history": []}


_HELD: dict[pathlib.Path, list[int]] = {}  # runs folder -> [lock fd, depth, owning thread], this process's
_HELD_LOCK = threading.Lock()


@contextlib.contextmanager
def exclusive(runs: pathlib.Path = RUNS):
    """One invocation at a time on a runs folder (CMP-1-02): each reads the
    state, works and saves it, so two at once would publish whichever saved
    last. An exclusive lock on `runs/.lock`, held for the whole invocation and
    reentrant within it — `compare.py` builds and draws inside its own —; a
    second invocation is refused, never queued. The invocation is the thread
    that took the lock: another thread of the same process is another
    invocation, refused like another process (CMP-2-09)."""
    me = threading.get_ident()
    runs.mkdir(parents=True, exist_ok=True)
    key = runs.resolve()
    with _HELD_LOCK:
        held = _HELD.get(key)
        if held is not None and held[2] != me:
            raise Refused(f"another invocation is running on {runs} (in this process)")
        if held is not None:
            held[1] += 1
    if held is not None:
        try:
            yield
        finally:
            with _HELD_LOCK:
                held[1] -= 1
        return
    fd = os.open(runs / ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise Refused(f"another invocation is running on {runs} (its .lock is held)") from None
    with _HELD_LOCK:
        _HELD[key] = [fd, 1, me]
    try:
        yield
    finally:
        with _HELD_LOCK:
            del _HELD[key]
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def serialized(fn):
    """`fn` under `exclusive` on the runs folder it is given, `RUNS` by default."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with exclusive(kwargs.get("runs", RUNS)):
            return fn(*args, **kwargs)
    return wrapper


def load(runs: pathlib.Path = RUNS) -> dict:
    path = runs / "state.json"
    return {**_empty(), **json.loads(path.read_text(encoding="utf-8"))} if path.is_file() else _empty()


def save(state: dict, runs: pathlib.Path = RUNS) -> None:
    runs.mkdir(parents=True, exist_ok=True)
    tmp = runs / f".state.{secrets.token_hex(4)}.json"
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, runs / "state.json")


def discard(state: dict, why: str) -> None:
    """The draw, both artifacts and every measure, gone — recorded with why."""
    gone = {k: state[k] for k in ("draw", "artifacts", "measures") if state[k]}
    state.update(draw=None, artifacts={}, measures={})
    state["discarded"].append({"at": _now(), "why": why, "what": sorted(gone)})


def enter_harness(state: dict, inputs: dict[str, str]) -> None:
    """A changed harness discards the draw, the artifacts and the measures, and
    closes the records made under the old one into `history`, kept and
    reported: a verdict judges the runs of one harness, the one that compares
    the candidates, never a run its oracle did not judge. Returning to a
    harness already closed brings its records back, every one, in their order:
    they are that harness's evidence, and a candidate it built is still judged
    by them (CMP-1-03)."""
    if state["harness"] is not None and state["harness"] != inputs:
        discard(state, "the harness inputs changed")
        if state["records"]:
            state["history"].append({"harness": state["harness"], "closed": _now(), "records": state["records"]})
        back = [h for h in state["history"] if h["harness"] == inputs]
        state["history"] = [h for h in state["history"] if h["harness"] != inputs]
        state["records"] = [r for h in back for r in h["records"]]
    state["harness"] = inputs


def records(state: dict) -> list[v.Record]:
    return [v.Record(**{**r, "stages": {k: v.Stage(**s) for k, s in r["stages"].items()}}) for r in state["records"]]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- a build of the encrypted route -----------------------------------------------------------

def prove_sandbox() -> sb.Proof:
    """§5: the probe through the wrapper the phase uses, before the phase."""
    with tempfile.TemporaryDirectory(prefix="bice-route-") as tmp, \
            sb.planted(pathlib.Path(tmp) / "sentinel") as sentinel, \
            sb.planted(roots.CLEAR / f"planted-{secrets.token_hex(4)}") as clear_sentinel:
        work = pathlib.Path(tmp) / "probe-work"
        work.mkdir()
        return sb.prove(work, absent=sb.host_absent(REPO, sentinel, clear_sentinel))


def own_allowlist(commit: str) -> al.Allowlist:
    """B's build inputs: its tracked sources and the envelope's reader, at the
    commit. No fixture, no package, no clear-mode file (§2.2)."""
    return al.tracked(commit, "prototypes/framework/own/") + al.tracked(commit, "web/envelope.mjs")


@serialized
def build(candidate: str, commit: str, allow: al.Allowlist, argv: list[str], output: str, *, runs: pathlib.Path = RUNS,
          require_clean: bool = True, prove=prove_sandbox, timeout: float = 3600, env: dict[str, str] | None = None,
          install=None) -> dict:
    """One build invocation: recorded first — so that an interrupted one still
    discards what came before —, then the sandbox's proof, the work folder from
    the allowlist and its check, the build with no network, the copy-out and
    the archive."""
    state = load(runs)
    enter_harness(state, harness_inputs(commit, require_clean=require_clean))
    run_id = f"{candidate}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(4)}"
    folder = runs / candidate / run_id
    folder.mkdir(parents=True)
    build_input = al.archive_list(allow, folder / "allowlist.json")
    entry = {"id": run_id, "candidate": candidate, "commit": commit, "build_input": build_input, "harness": state["harness"],
             "started": _now(), "status": "started"}
    discard(state, f"build {run_id} of {candidate}")
    state["builds"][candidate] = entry
    record = v.Record(run_id, build_input=build_input, stages={"build": v.Stage(status="interrupted")})
    state["records"].append(dataclasses.asdict(record))
    save(state, runs)

    def finish(stages: dict[str, v.Stage], **extra) -> dict:
        entry.update(extra, finished=_now())
        if extra.get("status") != "archived":  # a failed invocation keeps its logs and lists, not its trees
            for name in ("work", "node_modules", "install-work"):
                shutil.rmtree(folder / name, ignore_errors=True)
        state["records"][-1] = dataclasses.asdict(dataclasses.replace(record, builder_digest=extra.get("builder_digest"), stages=stages))
        save(state, runs)
        return entry

    proof = prove()
    entry["sandbox_proof"] = {"passed": proof.passed, "checks": proof.checks}
    if not proof.passed:
        return finish({"build": v.Stage(status="error")}, status="sandbox probe failed")
    if install is not None:  # a phase of its own before the build, also offline: its output joins the build's inputs
        installed = install(folder, entry)
        save(state, runs)
        if installed is None:
            return finish({"build": v.Stage(status="error")}, status="install failed")
        allow = allow + installed
        al.archive_list(allow, folder / "build-allowlist.json")
    work = folder / "work"
    al.assemble(allow, work)
    al.check(allow, work)
    t0 = time.time()
    done = sb.run(work, argv, timeout=timeout, env=env)
    seconds = round(time.time() - t0, 2)
    (folder / "build.log").write_bytes(b"$ " + " ".join(argv).encode() + b"\n" + done.stdout + b"\n--- stderr\n" + done.stderr)
    if done.returncode != 0:
        return finish({"build": v.Stage(status="error")}, status=f"build exited {done.returncode}", seconds=seconds)
    builder = folder / "builder"
    uncarried = al.copy_out(work, output, builder)
    if uncarried:
        return finish({"build": v.Stage(status="error")}, status="the build wrote entries no copy can carry", uncarried=uncarried)
    shutil.rmtree(work)
    digest = trees.archive(builder, folder / "builder.tar.gz")
    files = [p for p in builder.rglob("*") if p.is_file()]
    try:
        still(commit, entry["harness"], require_clean=require_clean)  # CMP-2-02
    except Refused as changed:
        finish({"build": v.Stage(status="interrupted")}, status=f"refused: {changed}")
        raise
    return finish({"build": v.Stage(), "archive": v.Stage()}, status="archived", builder_digest=digest,
                  archive=str((folder / "builder.tar.gz").relative_to(runs)), seconds=seconds,
                  files=len(files), bytes=sum(p.stat().st_size for p in files))


def build_own(commit: str, **kwargs) -> dict:
    return build("own", commit, own_allowlist(commit), OWN_BUILD, "build", **kwargs)


def evidence_sources(commit: str) -> al.Allowlist:
    """Evidence's encrypted route's sources (§3): the project's tracked files
    with no source — `sources/` left out — and the encrypted page in place of
    the clear one: `encrypted/pages/` as `pages/`, `encrypted/components/` as
    `components/`, and the envelope's reader as `components/envelope.mjs`."""
    out = []
    for e in al.tracked(commit, "prototypes/framework/evidence/").entries:
        if e.dest.startswith(("sources/", "pages/")):
            continue
        if e.dest.startswith("encrypted/"):
            rest = e.dest[len("encrypted/"):]
            if not rest.startswith(("pages/", "components/")):
                continue
            e = dataclasses.replace(e, dest=rest)
        out.append(e)
    envelope = al.tracked(commit, "web/envelope.mjs").entries[0]
    out.append(dataclasses.replace(envelope, dest="components/envelope.mjs"))
    return al.Allowlist(tuple(out))


def evidence_install(commit: str, runs: pathlib.Path):
    """The install phase of Evidence's encrypted route: the lockfile's tarballs
    fetched by the harness into this route's own cache — never the clear
    mode's (§2.2) —, `npm ci --offline --ignore-scripts` in the sandbox, and the
    kept `node_modules/` as the build's input."""
    def install(folder: pathlib.Path, entry: dict) -> al.Allowlist | None:
        lock = folder / "package-lock.json"
        lock.write_bytes(subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:prototypes/framework/evidence/package-lock.json"],
                                        check=True, capture_output=True).stdout)
        t0 = time.time()
        fetched = npm.fetch(lock, runs / "evidence-npm")
        entry["fetch"] = {"tarballs": len(fetched["tarballs"]), "downloaded": fetched["downloaded"], "from_cache": fetched["from_cache"],
                          "seconds": round(time.time() - t0, 1), "lockfile_sha256": fetched["lockfile_sha256"]}  # a cold fetch only with nothing from the cache (CMP-1-12)
        sources = al.Allowlist(tuple(e for e in al.tracked(commit, "prototypes/framework/evidence/").entries
                                     if e.dest in ("package.json", "package-lock.json", ".npmrc")))
        work = folder / "install-work"
        t0 = time.time()
        done = npm.install(sources + npm.cache_allowlist(runs / "evidence-npm", fetched), work, timeout=3600)
        entry["install"] = {"exit": done.returncode, "seconds": round(time.time() - t0, 1)}
        (folder / "install.log").write_bytes(done.stdout + b"\n--- stderr\n" + done.stderr)
        if done.returncode != 0:
            return None
        kept = npm.keep_install(work, folder / "node_modules")
        shutil.rmtree(work)
        entry["install"]["node_modules_entries"] = len(kept.entries)
        return kept
    return install


def build_evidence(commit: str, *, runs: pathlib.Path = RUNS, **kwargs) -> dict:
    return build("evidence", commit, evidence_sources(commit), EVIDENCE_BUILD, "build", runs=runs, env=EVIDENCE_ENV,
                 install=evidence_install(commit, runs), **kwargs)


def probe_page(candidate: str, *, runs: pathlib.Path = RUNS) -> dict:
    """A probe of a candidate's last archived builder output in the browser
    (A2, A3, A4 for Evidence): the archive extracted, assembled with the
    clear-mode fixture's validated package — a probe artifact, never judged,
    kept out of the run's records —, served on 127.0.0.1 and driven by
    `browser/smoke.mjs` with a wrong password, then the showcase's public one
    (N22). Written to the build's folder as `probe.json`."""
    import clear_mode as cm
    import harness as h
    import serve

    entry = load(runs)["builds"][candidate]
    folder = runs / candidate / entry["id"]
    probe = folder / "probe"
    if probe.exists():
        shutil.rmtree(probe)
    builder = probe / "builder"
    trees.extract(runs / entry["archive"], builder, entry["builder_digest"])
    fx, fixture_dir = cm.clear_fixture(cm.CLEAR / "evidence")
    assembly, _ = h.assemble(builder, fixture_dir / "package", fx.rows(), probe / "artifact")
    out = {"builder_digest": entry["builder_digest"], "assembly": assembly.cls, "assembly_message": assembly.message}
    if assembly.cls == h.PASS:
        opens_with = json.loads((h.DECLARATIONS / "profiles.json").read_text(encoding="utf-8"))["profiles"][0]["password"]  # N22, public
        with serve.Server(probe / "artifact") as server:
            subprocess.run(["node", str(HERE / "browser" / "smoke.mjs"), server.url, str(probe / "smoke.json"), str(probe / "smoke.png")],
                           capture_output=True, text=True, timeout=900, env={**os.environ, "BICE_OPENS_WITH": opens_with})
        out["smoke"] = json.loads((probe / "smoke.json").read_text(encoding="utf-8"))
    (folder / "probe.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("candidate", choices=["own", "evidence"])
    parser.add_argument("--commit", help="the commit whose tracked sources are built, and whose harness runs")
    parser.add_argument("--probe", action="store_true", help="open the last archived builder output in the browser, with the clear package")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe_page(args.candidate), indent=1))
        raise SystemExit(0)
    if not args.commit:
        parser.error("--commit is required for a build")
    pinned(args.commit, "route.py", sys.argv[1:])
    result = (build_own if args.candidate == "own" else build_evidence)(args.commit)
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result["status"] == "archived" else 1)
