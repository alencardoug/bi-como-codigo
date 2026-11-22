"""The clear mode of a candidate, and probes A6 and A1 (docs/framework_prototype.md §2.1, §2.2,
§3, §5, §7 step 2).

Everything lives under `prototypes/framework/clear/`, which the encrypted route never binds: the
clear-mode fixture, of its own seed; the candidate's npm cache for this mode; the install's and the
build's work folders, each assembled fresh from an allowlist and checked before its phase; the
copied-out builder output and query caches; and `record.json`, what each phase did.

    uv run --frozen --group prototype python prototypes/framework/clear_mode.py evidence --commit <sha>

A6 is the install with `npm ci --offline --ignore-scripts`, run first, in the sandbox with no
network, and the build after it, also with no network: whether they succeed with no script of a
dependency. A1 is the inspection of what the build wrote, with the clear-mode fixture's needles:
every carrier its rows and results land in, and whether a prerendered query result holds them.
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
import sandbox as sb
import trees

HERE = pathlib.Path(__file__).resolve().parent
CLEAR = HERE / "clear"
#: The clear-mode fixture's seed: its own, never the measured fixture's (§2.1).
CLEAR_SEED = 20261121

#: What Evidence writes that may carry the rows, copied out of the build's work folder (§3, A1).
EVIDENCE_OUTPUTS = ("build", ".svelte-kit", ".evidence", "static")
EVIDENCE_BUILD = "npm run sources && npm run build"


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


def evidence(commit: str, *, root: pathlib.Path = CLEAR / "evidence", fresh: bool = False) -> dict:
    """A6 and A1 for Evidence, in the clear mode."""
    if fresh and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    record: dict = {"candidate": "evidence", "commit": commit, "seed": CLEAR_SEED, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    log = root / "record.json"
    fx, fixture_dir = clear_fixture(root)
    parquet = fixture_dir / "p01.parquet"
    record["fixture"] = {"parquet_sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(), "rows": len(fx.rows()), "k": fx.k}

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
    built = sb.run(build_work, ["/usr/bin/sh", "-c", EVIDENCE_BUILD], timeout=3600,
                   env={"HOME": f"{sb.WORK}/.home", "EVIDENCE_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1",
                        "NODE_OPTIONS": "--max-old-space-size=4096"})
    record["A6_build"] = {"argv": EVIDENCE_BUILD, "exit": built.returncode, "seconds": round(time.time() - t0, 1),
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


def _by_file(findings) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for f in findings:
        codes = out.setdefault(f.file, {})
        codes[f.code] = codes.get(f.code, 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("candidate", choices=["evidence"])
    parser.add_argument("--commit", required=True, help="the commit whose tracked candidate sources are built")
    parser.add_argument("--fresh", action="store_true", help="remove the candidate's clear folder first")
    parser.add_argument("--inventory-only", action="store_true", help="redo A1 on the outputs already copied out")
    args = parser.parse_args()
    if args.inventory_only:
        log = CLEAR / "evidence" / "record.json"
        result = json.loads(log.read_text(encoding="utf-8"))
        kept = al.files(CLEAR / "evidence" / "node_modules", "node_modules/")
        result["A1"].update(inventory(CLEAR / "evidence" / "outputs", result["A1"]["copied"], clear_fixture(CLEAR / "evidence")[0],
                                      frozenset(e.sha256 for e in kept.entries)))
        _log(result, log)
    else:
        result = evidence(args.commit, fresh=args.fresh)
    summary = {k: ({kk: vv for kk, vv in v.items() if kk not in ("stderr", "stdout", "carriers")} if isinstance(v, dict) else v)
               for k, v in result.items()}
    print(json.dumps(summary, indent=1, default=str))
