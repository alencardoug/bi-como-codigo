"""The clear mode of a candidate, and probes A6 and A1 (docs/framework_prototype.md §2.1, §2.2,
§3, §5, §7 step 2).

Everything lives under `prototypes/framework/clear/`, which the encrypted route never binds: the
clear-mode fixture, of its own seed; the candidate's npm cache for this mode; the install's and the
build's work folders, each assembled fresh from an allowlist and checked before its phase; the
copied-out builder output and query caches; and `record.json`, what each phase did.

    uv run --frozen --group prototype python prototypes/framework/clear_mode.py evidence --commit <sha>
    uv run --frozen --group prototype python prototypes/framework/clear_mode.py own --commit <sha>

A6 is the install with `npm ci --offline --ignore-scripts`, run first, in the sandbox with no
network, and the build after it, also with no network: whether they succeed with no script of a
dependency. A1 is the inspection of what the build wrote, with the clear-mode fixture's needles:
every carrier its rows and results land in, and whether a prerendered query result holds them.

Candidate B, the own build, installs nothing: its clear build is `build.py clear`, run with the
system's Python in the sandbox with no network, over its tracked sources, the envelope's reader and
the clear-mode fixture's Parquet, which the page fetches after login (§2.5.5, "Clear mode").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import time

import allowlist as al
import fixture as fx_mod
import inspect_output as io_
import npm_offline as npm
import roots
import sandbox as sb
import trees

HERE = pathlib.Path(__file__).resolve().parent
CLEAR = roots.CLEAR
#: The clear-mode fixture's seed: its own, never the measured fixture's (§2.1).
CLEAR_SEED = 20261121

#: What Evidence writes that may carry the rows, copied out of the build's work folder (§3, A1).
EVIDENCE_OUTPUTS = ("build", ".svelte-kit", ".evidence", "static")
EVIDENCE_BUILD = "npm run sources && npm run build"
#: Probe A7: the same build with Vite's configuration of ours, which loads the engine from jsDelivr (§3).
EVIDENCE_BUILD_PINNED = "npm run sources && npm run build:pinned"


def _log(record: dict, path: pathlib.Path) -> None:
    path.write_text(json.dumps(record, indent=1, default=str) + "\n", encoding="utf-8")


def _tail(data: bytes, n: int = 4000) -> str:
    return data.decode("utf-8", "replace")[-n:]


def clear_fixture(root: pathlib.Path) -> tuple[fx_mod.Fixture, pathlib.Path]:
    """The clear-mode fixture, written once under `root/fixture/`."""
    fx, _ = fx_mod.generate(CLEAR_SEED)
    out = root / "fixture"
    if not out.exists():
        fx_mod.write(fx, out)
    return fx, out


def evidence(commit: str, *, root: pathlib.Path = CLEAR / "evidence", fresh: bool = False, build: str = EVIDENCE_BUILD,
             install_from: pathlib.Path | None = None) -> dict:
    """A6 and A1 for Evidence, in the clear mode. `build` is the build's
    command; `install_from`, a candidate clear folder whose fetch and kept
    install are reused — only for the same lockfile, by digest — instead of
    fetching and installing again."""
    if fresh and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    record: dict = {"candidate": "evidence", "commit": commit, "seed": CLEAR_SEED, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    log = root / "record.json"
    fx, fixture_dir = clear_fixture(root)
    parquet = fixture_dir / "p01.parquet"
    record["fixture"] = {"parquet_sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(), "rows": len(fx.rows()), "k": fx.k}
    if install_from is not None:
        return _build_evidence(commit, root, record, log, fx, parquet, build, install_from)

    sources = al.tracked(commit, "prototypes/framework/evidence/")
    tracked_lock = root / "package-lock.json"  # the commit's own lockfile, as the allowlist has it
    tracked_lock.write_bytes(subprocess.run(["git", "-C", str(HERE), "show", f"{commit}:prototypes/framework/evidence/package-lock.json"],
                                            check=True, capture_output=True).stdout)
    t0 = time.time()
    fetched = npm.fetch(tracked_lock, root / "npm")
    record["fetch"] = {"tarballs": len(fetched["tarballs"]), "seconds": round(time.time() - t0, 1), "lockfile_sha256": fetched["lockfile_sha256"]}
    _log(record, log)

    # A6: the install, offline, with no script of a dependency.
    install_work = root / "install-work"
    if install_work.exists():
        shutil.rmtree(install_work)
    allow_install = sources + npm.cache_allowlist(root / "npm", fetched)
    t0 = time.time()
    done = npm.install(allow_install, install_work, timeout=3600)
    record["A6_install"] = {"argv": npm.INSTALL, "exit": done.returncode, "seconds": round(time.time() - t0, 1),
                            "stderr": _tail(done.stderr), "stdout": _tail(done.stdout)}
    _log(record, log)
    if done.returncode != 0:
        return record
    modules_dir = root / "node_modules"
    if modules_dir.exists():
        shutil.rmtree(modules_dir)
    modules = npm.keep_install(install_work, modules_dir)
    record["A6_install"]["node_modules_entries"] = len(modules.entries)
    return _build_evidence(commit, root, record, log, fx, parquet, build, root)


def _build_evidence(commit: str, root: pathlib.Path, record: dict, log: pathlib.Path, fx, parquet: pathlib.Path, build: str,
                    install: pathlib.Path) -> dict:
    """The build phase, offline, over the sources at `commit`, the kept install
    of `install` and the clear Parquet; then A1's inventory."""
    sources = al.tracked(commit, "prototypes/framework/evidence/")
    if install != root:
        mine = subprocess.run(["git", "-C", str(HERE), "show", f"{commit}:prototypes/framework/evidence/package-lock.json"],
                              check=True, capture_output=True).stdout
        theirs = json.loads((install / "record.json").read_text(encoding="utf-8"))
        if theirs.get("fetch", {}).get("lockfile_sha256") != hashlib.sha256(mine).hexdigest() or theirs.get("A6_install", {}).get("exit") != 0:
            raise SystemExit(f"{install} holds no install of this lockfile")
        record["install_reused"] = {"from": str(install.relative_to(HERE)), "lockfile_sha256": hashlib.sha256(mine).hexdigest()}
    modules = al.files(install / "node_modules", "node_modules/")

    # The build, offline, in a fresh work folder: the sources, the install's node_modules, and the
    # clear-mode fixture as P01's source (the clear mode only).
    build_work = root / "build-work"
    if build_work.exists():
        shutil.rmtree(build_work)
    extensions = npm.pinned(HERE / "evidence" / "extensions.json", root / "pinned")  # A6: what the build loads at run time
    record["A6_build_inputs"] = [{"path": e.dest, "sha256": e.sha256} for e in extensions.entries]
    allow_build = sources + modules + extensions + al.single("sources/p01/p01.parquet", parquet)
    al.assemble(allow_build, build_work)
    al.check(allow_build, build_work)
    t0 = time.time()
    built = sb.run(build_work, ["/usr/bin/sh", "-c", build], timeout=3600,
                   env={"HOME": f"{sb.WORK}/.home", "EVIDENCE_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1",
                        "NODE_OPTIONS": "--max-old-space-size=4096"})
    record["A6_build"] = {"argv": build, "exit": built.returncode, "seconds": round(time.time() - t0, 1),
                          "stderr": _tail(built.stderr), "stdout": _tail(built.stdout)}
    _log(record, log)
    if built.returncode != 0:
        return record

    # A1: what the build wrote, copied out by the harness, inspected with the clear fixture's needles.
    outputs = root / "outputs"
    if outputs.exists():
        shutil.rmtree(outputs)
    outputs.mkdir()
    copied = {}
    for rel in EVIDENCE_OUTPUTS:
        if (build_work / rel).is_dir() and not (build_work / rel).is_symlink():
            copied[rel] = al.copy_out(build_work, rel, outputs / rel)
    record["A1"] = {"copied": sorted(copied), "uncarried": {k: v for k, v in copied.items() if v}}
    record["A1"].update(inventory(outputs, sorted(copied), fx, frozenset(e.sha256 for e in modules.entries)))
    _log(record, log)
    return record


OWN_BUILD = ["/usr/bin/python3", "-I", "build.py", "clear"]


def own(commit: str, *, root: pathlib.Path = CLEAR / "own", fresh: bool = False) -> dict:
    """The clear mode of Candidate B: its build, in the sandbox with no network,
    over its tracked sources, the envelope's reader and the clear-mode
    fixture's Parquet; then the same inventory as Evidence's A1."""
    if fresh and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    record: dict = {"candidate": "own", "commit": commit, "seed": CLEAR_SEED, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    log = root / "record.json"
    fx, fixture_dir = clear_fixture(root)
    parquet = fixture_dir / "p01.parquet"
    record["fixture"] = {"parquet_sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(), "rows": len(fx.rows()), "k": fx.k}

    build_work = root / "build-work"
    if build_work.exists():
        shutil.rmtree(build_work)
    allow = al.tracked(commit, "prototypes/framework/own/") + al.tracked(commit, roots.ENVELOPE) + al.single("data/p01.parquet", parquet)
    record["build_inputs"] = {"allowlist_sha256": allow.digest, "files": len(allow.entries)}
    al.assemble(allow, build_work)
    al.check(allow, build_work)
    t0 = time.time()
    built = sb.run(build_work, OWN_BUILD, timeout=600)
    record["build"] = {"argv": OWN_BUILD, "exit": built.returncode, "seconds": round(time.time() - t0, 1),
                       "stderr": _tail(built.stderr), "stdout": _tail(built.stdout)}
    _log(record, log)
    if built.returncode != 0:
        return record

    outputs = root / "outputs"
    if outputs.exists():
        shutil.rmtree(outputs)
    outputs.mkdir()
    uncarried = al.copy_out(build_work, "build", outputs / "build")
    record["A1"] = {"copied": ["build"], "uncarried": {"build": uncarried} if uncarried else {}}
    record["A1"].update(inventory(outputs, ["build"], fx, frozenset()))
    _log(record, log)
    return record


def smoke(root: pathlib.Path = CLEAR / "own", *, cdn: pathlib.Path = HERE / "own" / "cdn.json", passive: bool = False) -> dict:
    """B's clear build served on 127.0.0.1 by the stage's server and opened in
    headless Chrome by `browser/smoke.mjs`: that the page loads its pinned
    bodies from jsDelivr, opens the clear Parquet after submit, shows G, Z and
    the partial month, and logs out; and every URL of jsDelivr or of DuckDB's
    extensions it reached that `cdn.json` does not declare. A record, not the
    check of §2.6. `passive` only opens the page and waits for its tables:
    Evidence's page has no login of the clear mode to drive."""
    import serve

    log = root / "record.json"
    record = json.loads(log.read_text(encoding="utf-8"))
    out = root / "smoke.json"
    out.unlink(missing_ok=True)
    with serve.Server(root / "outputs" / "build") as server:
        done = subprocess.run(["node", str(HERE / "browser" / "smoke.mjs"), server.url + ("" if passive else "index.html"), str(out),
                               str(root / "smoke.png"), *(["--passive"] if passive else [])],
                              capture_output=True, text=True, timeout=600)
    record["smoke"] = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {"exit": done.returncode, "stderr": done.stderr[-4000:]}
    declared = {f["url"] for f in json.loads(cdn.read_text(encoding="utf-8"))["files"]}
    third = ("https://cdn.jsdelivr.net/", "https://extensions.duckdb.org/")
    if isinstance(record["smoke"].get("cdn_urls"), list):  # what the page reached of the declared hosts and was not declared
        record["smoke"]["undeclared"] = sorted(u for u in record["smoke"]["cdn_urls"] if u.startswith(third) and u not in declared)
    _log(record, log)
    return record["smoke"]


def a7(root: pathlib.Path) -> dict:
    """What of the engine A7's build still carries: every WASM file and every
    file holding DuckDB-WASM's worker, by name and size, and the bytes of the
    published `build/`."""
    build = root / "outputs" / "build"
    if not build.is_dir():
        return {"built": False}
    files = [p for p in build.rglob("*") if p.is_file()]
    wasm = sorted((p.relative_to(build).as_posix(), p.stat().st_size) for p in files if p.suffix == ".wasm")
    workers = sorted((p.relative_to(build).as_posix(), p.stat().st_size) for p in files
                     if p.suffix == ".js" and b"duckdb_web_" in p.read_bytes())
    pinned = sorted({f["url"] for f in json.loads((HERE / "evidence" / "cdn.json").read_text(encoding="utf-8"))["files"]
                     if any(f["url"].encode() in p.read_bytes() for p in files if p.suffix == ".js")})
    return {"built": True, "wasm_files": wasm, "engine_worker_files": workers, "pinned_urls_in_build": pinned,
            "build_bytes": sum(p.stat().st_size for p in files), "build_files": len(files)}


def inventory(outputs: pathlib.Path, copied: list[str], fx: fx_mod.Fixture, dependencies: frozenset[str]) -> dict:
    """A1: every copied-out file inspected with the clear fixture's needles, by
    carrier, and the query results the build wrote — wherever under the
    outputs Evidence put them (its SvelteKit project lives in
    `.evidence/template/`). A binary byte-identical to a file of the kept
    install, by `dependencies`, is recorded, not inconclusive (§2.5.2)."""
    needles = io_.Needles.from_fixture(fx)
    carriers: dict[str, dict] = {}
    for rel in copied:
        items = [io_.Item(f"{rel}/{name}", data) for name, data in sorted(trees.files(outputs / rel).items())]
        report = io_.inspect_items(items, needles, dependencies=dependencies)
        carriers[rel] = {
            "files": len(items),
            "findings_by_file": _by_file(report.findings),
            "inconclusive": [{"file": n.file, "path": n.path, "reason": n.reason} for n in report.inconclusive],
            "recorded": len(report.recorded),
        }
    prerendered = sorted(f for c in carriers.values() for f in c["findings_by_file"] if "/prerendered_queries/" in f)
    return {"carriers": carriers, "queries_at_build_time": bool(prerendered), "prerendered_query_files_with_rows": prerendered}


#: The media types of a clear-mode control's gate run: what Evidence's carriers are served as.
CONTROL_LISTS = ("site/*\n", "".join(f"{x} application/octet-stream\n" for x in (".html", ".js", ".json", ".bice", ".parquet", ".arrow")))


def data_carriers(findings_by_file: dict[str, dict]) -> list[str]:
    """The files of `build/` A1 found the clear fixture in that are Evidence's
    carriers of it: the source's Parquet under `data/`, the query results under
    `api/prerendered_queries/`, and the prerendered pages. A number hit in the
    bundled code or in the query index is a coincidence of the clear fixture,
    which is not drawn against the builder output (§3), and is no carrier."""
    return sorted(f for f in findings_by_file if f.startswith("build/") and (
        f.startswith(("build/data/", "build/api/prerendered_queries/")) or f.endswith(".html")))


def own_carriers(findings_by_file: dict[str, dict]) -> list[str]:
    """Every file of B's `build/` A1 found the clear fixture in: the own build
    bundles no third party, so a hit there is a carrier, never a coincidence
    set aside."""
    return sorted(f for f in findings_by_file if f.startswith("build/"))


CARRIERS = {"evidence": data_carriers, "own": own_carriers}


def controls(candidate: str = "evidence", root: pathlib.Path | None = None) -> list[dict]:
    """The clear mode's controls of §2.5.5: each carrier A1 found, copied
    **alone** into a clean artifact — a hand-made builder output and the
    clear fixture's validated package —, and diagnosed there: `verify`'s class,
    the inspection's codes in that file and elsewhere, and the verdict of that
    one run. The candidate's own builder output takes the carriers at step 5."""
    import harness as h
    import verdict as v

    root = root or CLEAR / candidate
    log = root / "record.json"
    record = json.loads(log.read_text(encoding="utf-8"))
    fx, fixture_dir = clear_fixture(root)
    needles = io_.Needles.from_fixture(fx)
    outputs = root / "outputs"
    work = root / "controls"
    if work.exists():
        shutil.rmtree(work)
    made = work / "made"
    made.mkdir(parents=True)
    (made / "index.html").write_text("<!doctype html><title>P01</title>")
    archive_digest = h.archive(made, work / "builder.tar.gz")  # archived, then inspected from the archive
    builder = work / "builder"
    h.extract(work / "builder.tar.gz", builder, archive_digest)
    built = io_.inspect_dir(builder, needles)
    lists = work / "lists"
    lists.mkdir()
    (lists / "include.txt").write_text(CONTROL_LISTS[0])
    (lists / "media_types.txt").write_text(CONTROL_LISTS[1])
    out = []
    for i, rel in enumerate(CARRIERS[candidate](record["A1"]["carriers"]["build"]["findings_by_file"])):
        dest = f"{candidate}/" + rel[len("build/"):]
        artifact = work / f"artifact{i}"
        assembly, validated = h.assemble(builder, fixture_dir / "package", fx.rows(), artifact,
                                         control_additions={dest: (outputs / rel).read_bytes()})
        if assembly.cls != h.PASS:
            out.append({"carrier": rel, "assembly": assembly.cls, "message": assembly.message})
            continue
        result = h.verify(artifact, builder, h.write_root(work / f"run{i}", lists), validated, label="control")
        inspected = io_.inspect_dir(artifact, needles, validated=dict(validated.files))
        stages = {"build": v.Stage(), "archive": v.Stage(),
                  "inspect_builder": v.Stage(findings=len(built.findings), inconclusive=len(built.inconclusive)),
                  "assembly": v.Stage(cls=assembly.cls), "verify": v.Stage(cls=result.cls),
                  "inspect_artifact": v.Stage(findings=len(inspected.findings), inconclusive=len(inspected.inconclusive))}
        artifact_digest = hashlib.sha256(json.dumps(h.tree(artifact)).encode()).hexdigest()
        judged = v.verdict([v.Record(f"control{i}", build_input="clear-control", builder_digest=archive_digest,
                                     artifact_digest=artifact_digest, stages=stages)])  # this one run, judged alone
        out.append({
            "carrier": rel, "as": dest, "verify": result.cls, "verify_message": result.message,
            "codes_in_carrier": sorted({x.code for x in inspected.findings if x.file == dest}),
            "codes_elsewhere": sorted({x.code for x in inspected.findings if x.file != dest}),
            "inconclusive": len(inspected.inconclusive), "verdict": judged.name,
        })
    record["controls"] = out
    _log(record, log)
    return out


def _by_file(findings) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for f in findings:
        codes = out.setdefault(f.file, {})
        codes[f.code] = codes.get(f.code, 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("candidate", choices=["evidence", "own"])
    parser.add_argument("--commit", required=True, help="the commit whose tracked candidate sources are built")
    parser.add_argument("--fresh", action="store_true", help="remove the candidate's clear folder first")
    parser.add_argument("--inventory-only", action="store_true", help="redo A1 on the outputs already copied out")
    parser.add_argument("--controls", action="store_true", help="run the clear mode's controls on A1's carriers")
    parser.add_argument("--smoke", action="store_true", help="open the clear build in headless Chrome (B), or A7's build (Evidence, with --a7)")
    parser.add_argument("--a7", action="store_true", help="Evidence only: probe A7, the build with the engine from jsDelivr, in clear/evidence-a7/")
    args = parser.parse_args()
    if args.smoke:
        if args.candidate == "own":
            print(json.dumps(smoke(), indent=1))
        elif args.a7:
            print(json.dumps(smoke(CLEAR / "evidence-a7", cdn=HERE / "evidence" / "cdn.json", passive=True), indent=1))
        else:
            raise SystemExit("--smoke is B's, or Evidence's with --a7")
        raise SystemExit(0)
    if args.a7:
        if args.candidate != "evidence":
            raise SystemExit("--a7 is Evidence's")
        result = evidence(args.commit, root=CLEAR / "evidence-a7", fresh=True, build=EVIDENCE_BUILD_PINNED, install_from=CLEAR / "evidence")
        result["A7"] = a7(CLEAR / "evidence-a7")
        _log(result, CLEAR / "evidence-a7" / "record.json")
        print(json.dumps({k: v for k, v in result.items() if k not in ("A1",)}, indent=1, default=str))
        raise SystemExit(0)
    if args.controls:
        print(json.dumps(controls(args.candidate), indent=1))
        raise SystemExit(0)
    if args.inventory_only:
        if args.candidate != "evidence":
            raise SystemExit("--inventory-only is Evidence's: B's build takes seconds")
        log = CLEAR / "evidence" / "record.json"
        result = json.loads(log.read_text(encoding="utf-8"))
        kept = al.files(CLEAR / "evidence" / "node_modules", "node_modules/")
        result["A1"].update(inventory(CLEAR / "evidence" / "outputs", result["A1"]["copied"], clear_fixture(CLEAR / "evidence")[0],
                                      frozenset(e.sha256 for e in kept.entries)))
        _log(result, log)
    else:
        result = (evidence if args.candidate == "evidence" else own)(args.commit, fresh=args.fresh)
    summary = {k: ({kk: vv for kk, vv in v.items() if kk not in ("stderr", "stdout", "carriers")} if isinstance(v, dict) else v)
               for k, v in result.items()}
    print(json.dumps(summary, indent=1, default=str))
