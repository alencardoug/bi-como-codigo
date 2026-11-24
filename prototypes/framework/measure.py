"""The measures of stage 2.3 (docs/framework_prototype.md §2.7, §6).

Five cold journeys, each in a new Chrome process with an empty profile; five
warm ones, each in its own fresh profile after two standard priming journeys
followed by quiescence (`browser/journey.mjs`). Of each: the four page marks
on one clock — every DevTools session's monotonic times mapped to wall time
through `Network.requestWillBeSent`'s pairs, the largest disagreement kept as
the clock's error —; navigation to summary and submit to summary; the bytes
of every request of every target, by origin, encoded bytes observed by each
cutoff — partial transfers labelled — and completed responses, with what was
served from cache and its size where one is known; and the sample's cache
evidence — per request, memory or disk cache, `304` or `200`; which scripts
consumed a compiled-code cache; whether the engine's WASM module came from
Chromium's cache. Warm samples whose evidence matches form one series; no
statistic is taken across series, and a sample whose trace lost data enters
none. Then what needs no browser: lines we wrote, dependencies, the build, the
gate's lists, the local files raw and brotli-compressed, and upkeep.
"""

from __future__ import annotations

import json
import pathlib
import re
import statistics
import subprocess
import tempfile
import urllib.request

import brotli

import roots
import serve
import trees

HERE = pathlib.Path(__file__).resolve().parent
REPO = roots.CHECKOUT  # its Git objects (CMP-3-03)
DRIVER = HERE / "browser" / "journey.mjs"
PASSWORD = "senha_complexa_123"  # the showcase's public password (N22)
COLD = WARM = 5
PRIMING = 2


# --- one journey ------------------------------------------------------------------------


def journey(artifact: pathlib.Path, expected: list[list[str]], priming: int, out: pathlib.Path, *, timeout: float = 1200) -> dict:
    with serve.Server(artifact) as server, tempfile.TemporaryDirectory(prefix="bice-measure-") as tmp:
        config = {"profile": str(pathlib.Path(tmp) / "profile"), "url": server.url, "password": PASSWORD,
                  "expected": expected, "priming": priming, "out": str(out)}
        path = pathlib.Path(tmp) / "config.json"
        path.write_text(json.dumps(config))
        subprocess.run(["node", str(DRIVER), str(path)], capture_output=True, timeout=timeout, check=False)
        raw = json.loads(out.read_text(encoding="utf-8"))
        raw["origin"] = server.url.rstrip("/")
        raw["served"] = len(server.log)
    return raw


def clocks(sessions: dict[str, list[list[float]]]) -> tuple[dict[str, float], float]:
    """Each session's offset from monotonic seconds to wall milliseconds — the
    median of its pairs — and the largest disagreement among a session's pairs."""
    offsets, error = {}, 0.0
    for s, pairs in sessions.items():
        diffs = [w * 1000 - t * 1000 for t, w in pairs]
        offsets[s] = statistics.median(diffs)
        error = max(error, max(diffs) - min(diffs))
    return offsets, error


def _origin(url: str, local: str) -> str:
    return "local" if url.startswith(local) else url.split("/")[2] if "://" in url else "other"


def cache_class(r: dict) -> str:
    if r.get("from_memory"):
        return "memory"
    if r.get("from_sw"):
        return "service worker"
    if r.get("from_disk"):
        return "disk"
    if r.get("wire_status") == 304 or r.get("status") == 304:
        return "304"
    if r.get("failed"):
        return "failed"
    return str(r.get("wire_status") or r.get("status") or "unknown")


#: The engine's module, by its URL; DuckDB's extensions are other modules.
ENGINE_WASM = re.compile(r"/duckdb-(?:eh|mvp|coi)\.wasm(?:\?|$)")
_CACHED = ("v8.wasm.cachedModule", "v8.wasm.moduleCacheHit")
#: Terminal evidence of a compilation: a streaming job's start is no evidence — the same job can end by
#: deserializing a cached module (CMP-3-08).
_COMPILED = ("wasm.BaselineFinished", "v8.wasm.compiledModule")


def trace_evidence(events: list[dict], requests: dict | None = None) -> dict:
    """From the trace: the scripts whose compile consumed a code cache — by their URL, query and
    all —, and how the engine's WASM module was obtained.

    The WebAssembly events name no module (`wasm.SetUrl` is empty), so the engine's are taken
    by time (CMP-2-08): those after the engine's WASM request was sent — `duckdb-eh.wasm` — and
    before the first request of DuckDB's extensions, another module; the trace's microseconds and
    the protocol's seconds are one monotonic clock. A module from Chromium's compiled-WASM cache
    is deserialized; one compiled streams through baseline compilation (FPROTO-8-04). With no
    engine request, or no event in its window, the engine is unattributed; with both kinds in
    it, unclassified (CMP-1-10). The basis of the inference is kept with it."""
    consumed, wasm = set(), []
    for e in events:
        name, data = e.get("name", ""), (e.get("args") or {}).get("data") or {}
        if name in ("v8.compile", "V8.CompileCode", "v8.compileModule") and (data.get("consumedCacheSize") or data.get("cacheConsumeOptions") == "code"):
            if data.get("url"):
                consumed.add(data["url"])
        if "wasm" in name.lower() or name.lower().startswith("v8.wasm"):
            wasm.append(e)
    sent = lambda pick: min((r["events"][0]["ts"] for r in (requests or {}).values()  # noqa: E731
                             if r.get("url") and r.get("events") and pick(r["url"])), default=None)
    engine = sent(lambda u: ENGINE_WASM.search(u))
    # The extension that closes the window is the first requested after the engine's: a prefetch
    # before it is no module after it (CMP-3-08).
    extension = None if engine is None else min((r["events"][0]["ts"] for r in (requests or {}).values()
                                                  if r.get("url") and r.get("events") and "extensions.duckdb.org/" in r["url"]
                                                  and r["events"][0]["ts"] >= engine), default=None)
    names = sorted({e.get("name", "") for e in wasm})
    if engine is None:
        return {"code_cache_consumed": sorted(consumed), "wasm_events": names, "wasm": "unattributed" if wasm else "unobserved",
                "wasm_basis": "no request of the engine's WASM in the journey"}
    window = [e for e in wasm if e.get("ts") is not None and e["ts"] / 1e6 >= engine and (extension is None or e["ts"] / 1e6 < extension)]
    cached = any(e["name"] in _CACHED or "deserial" in e["name"].lower() for e in window)
    compiled = any(e["name"] in _COMPILED for e in window)
    kind = "unclassified" if cached and compiled else "cached" if cached else "compiled" if compiled else ("unattributed" if wasm else "unobserved")
    # The basis names its events apart: the streaming job's start, and the first terminal event that
    # classes the module — the one the class rests on (CMP-4-05).
    after = lambda x: None if x is None else round((x - engine) * 1000, 1)  # noqa: E731
    starts = [e["ts"] / 1e6 for e in window if e["name"] == "wasm.StartStreamingCompilation"]
    terminal = min(((e["ts"] / 1e6, e["name"]) for e in window if e["name"] in _CACHED + _COMPILED or "deserial" in e["name"].lower()),
                   default=None)
    timing = {"start_ms": after(min(starts, default=None)), "terminal_ms": after(terminal and terminal[0]),
              "terminal_event": terminal and terminal[1],
              "terminal_before_extension_ms": None if terminal is None or extension is None else round((extension - terminal[0]) * 1000, 1)}
    if terminal is not None:
        basis = (f"{terminal[1]} at {timing['terminal_ms']} ms after the engine's WASM request"
                 + (f", {timing['terminal_before_extension_ms']} ms before the extension's" if extension is not None else "")
                 + (f"; its streaming job started at {timing['start_ms']} ms" if timing["start_ms"] is not None else ""))
    else:
        basis = "no terminal module event between the engine's WASM request and the extension's"
    return {"code_cache_consumed": sorted(consumed), "wasm_events": names, "wasm": kind, "wasm_basis": basis, "wasm_timing": timing}


def sample(raw: dict) -> dict:
    """One measured journey, counted."""
    m = raw.get("measured") or {}
    marks = {x["mark"]: x["t"] for x in m.get("marks", [])}
    offsets, error = clocks(m.get("sessions", {}))
    local = raw["origin"]
    # An event another session reported is on that session's clock (CMP-2-07).
    to_wall = lambda r, ts, s=None: ts * 1000 + offsets.get(s or r["session"], offsets.get(r["session"], next(iter(offsets.values()), 0.0)))  # noqa: E731
    cutoffs = {name: marks.get(name) for name in ("login_box", "summary")}
    requests, by_origin = [], {}
    for r in (m.get("requests") or {}).values():
        if not r.get("url") or not r["url"].startswith(("http://", "https://")):
            continue  # blob: and data: URLs are no network
        fin = r.get("finished")
        row = {"url": r["url"].split("?")[0], "key": r["url"], "origin": _origin(r["url"], local), "cache": cache_class(r),
               "encoding": r.get("encoding"), "status": r.get("status"), "wire_status": r.get("wire_status"),
               "encoded": fin["encoded"] if fin else None, "content_length": r.get("content_length"),
               "data_encoded": sum(e.get("encoded", 0) for e in r["events"] if e["e"] == "data"),
               "worker": r["session"] != m.get("page"),
               # answered, but no session reported its completion or failure: its bytes are unknown (CMP-2-07)
               "bytes_unknown": not fin and not r.get("failed") and (r.get("status") is not None or r.get("wire_status") is not None)}
        for name, cut in cutoffs.items():
            if cut is None:
                continue
            row[f"observed_by_{name}"] = sum(e.get("encoded", 0) for e in r["events"] if e["e"] == "data" and to_wall(r, e["ts"], e.get("s")) <= cut)
            row[f"completed_by_{name}"] = bool(fin and to_wall(r, fin["ts"], fin.get("s")) <= cut)
            if row[f"completed_by_{name}"]:
                row[f"observed_by_{name}"] = max(row[f"observed_by_{name}"], fin["encoded"])
            row[f"partial_at_{name}"] = row[f"observed_by_{name}"] > 0 and not row[f"completed_by_{name}"]
        hops = []
        for hop in r.get("hops", []):  # each redirect a response of its own, with its bytes (CMP-1-11)
            h_row = {"url": hop["url"].split("?")[0], "key": hop["url"], "origin": _origin(hop["url"], local), "cache": f"redirect {hop['status']}",
                     "encoding": None, "status": hop["status"], "wire_status": hop["status"], "encoded": hop.get("encoded") or 0,
                     "content_length": None, "data_encoded": 0, "worker": row["worker"]}
            for name, cut in cutoffs.items():
                if cut is None:
                    continue
                done = to_wall(r, hop["ts"], hop.get("s")) <= cut  # the hop's own session's clock (CMP-3-07)
                h_row.update({f"observed_by_{name}": h_row["encoded"] if done else 0, f"completed_by_{name}": done, f"partial_at_{name}": False})
            hops.append(h_row)
        for x in (*hops, row):
            requests.append(x)
            o = by_origin.setdefault(x["origin"], {"requests": 0, "encoded": 0})
            o["requests"] += 1
            o["encoded"] += x["encoded"] or 0
    totals = {}
    for name in cutoffs:
        totals[name] = {
            "observed": sum(r.get(f"observed_by_{name}", 0) for r in requests),
            "completed": sum(r["encoded"] or 0 for r in requests if r.get(f"completed_by_{name}")),
            "partial_requests": sum(1 for r in requests if r.get(f"partial_at_{name}")),
            "by_origin": {o: sum(r["encoded"] or 0 for r in requests if r["origin"] == o and r.get(f"completed_by_{name}")) for o in by_origin},
            "observed_by_origin": {o: sum(r.get(f"observed_by_{name}", 0) for r in requests if r["origin"] == o) for o in by_origin},
        }
    served = [{"url": r["url"], "cache": r["cache"], "size": r["content_length"] or "size unknown"}
              for r in requests if r["cache"] in ("memory", "disk", "304", "service worker")]
    evidence = trace_evidence(m.get("trace", []), m.get("requests"))
    # The local origin's port changes with every journey's server: a request is the same by its path there.
    path = lambda u: u[len(local):] if u.startswith(local) else u  # noqa: E731
    # By the URL each request asked for, query and all: two queries are two cache entries (CMP-2-08).
    signature = {"requests": sorted((path(r.get("key", r["url"])), r["cache"]) for r in requests),
                 "code_cache": sorted(path(u) for u in evidence["code_cache_consumed"]), "wasm": evidence["wasm"]}
    return {
        "error": raw.get("error"), "clock_error_ms": round(error, 3),
        "nav_to_summary_ms": round(marks["summary"] - marks["navigation"], 1) if {"summary", "navigation"} <= marks.keys() else None,
        "submit_to_summary_ms": round(marks["summary"] - marks["submit"], 1) if {"summary", "submit"} <= marks.keys() else None,
        "nav_to_login_box_ms": round(marks["login_box"] - marks["navigation"], 1) if {"login_box", "navigation"} <= marks.keys() else None,
        "bytes": totals, "by_origin": by_origin, "served_from_cache": served, "requests": requests,
        "accounting_mismatches": [r["url"] for r in requests if r["encoded"] is not None and r["data_encoded"] > r["encoded"]],
        "reconciliation": reconcile(totals, by_origin, requests),
        "trace_lost": m.get("trace_lost"), "cache_evidence": evidence, "signature": signature,
        "workers": m.get("workers", []), "primed": raw.get("primed", []),
    }


def reconcile(totals: dict, by_origin: dict, requests: list[dict]) -> list[str]:
    """The byte totals checked against each other (CMP-1-11): at each cutoff the
    origins add up to the total, observed and completed both, and nothing
    completed is more than was observed; the later cutoff holds at least what
    the earlier did; the whole journey's origins add up to its requests. Each
    failure named; none is an empty list."""
    bad = []
    for name, t in totals.items():
        if sum(t["by_origin"].values()) != t["completed"]:
            bad.append(f"{name}: completed by origin does not add up")
        if sum(t["observed_by_origin"].values()) != t["observed"]:
            bad.append(f"{name}: observed by origin does not add up")
        if t["completed"] > t["observed"]:
            bad.append(f"{name}: more completed than observed")
    if {"login_box", "summary"} <= totals.keys() and totals["summary"]["observed"] < totals["login_box"]["observed"]:
        bad.append("fewer bytes by the summary than by the login box")
    if sum(o["encoded"] for o in by_origin.values()) != sum(r["encoded"] or 0 for r in requests):
        bad.append("the journey's origins do not add up")
    bad += [f"bytes unknown: {r['url']}" for r in requests if r.get("bytes_unknown")]  # never reconciled by omission (CMP-2-07)
    return bad


def series(samples: list[dict]) -> dict:
    """Warm samples grouped by their cache evidence; a sample whose trace lost
    data, or whose journey failed, enters none (FPROTO-6-06, FPROTO-7-06); nor
    one whose priming was not complete — every priming journey with its summary,
    its requests finished, its logout confirmed and quiescence reached — or
    whose engine's WASM the trace cannot classify (CMP-1-10)."""
    groups: list[dict] = []
    apart = []
    for i, s in enumerate(samples):
        if (s["trace_lost"] or s["trace_lost"] is None or s["error"] or s["nav_to_summary_ms"] is None or not primed_complete(s)
                or s["signature"]["wasm"] in ("unclassified", "unobserved", "unattributed")):
            apart.append(i)
            continue
        for g in groups:
            if g["signature"] == s["signature"]:
                g["samples"].append(i)
                break
        else:
            groups.append({"signature": s["signature"], "samples": [i]})
    return {"series": [{"samples": g["samples"], **stats([samples[i] for i in g["samples"]]),
                        "wasm": g["signature"]["wasm"], "code_cache": g["signature"]["code_cache"],
                        "caches": sorted({c for _, c in g["signature"]["requests"]})} for g in groups],
            "apart": apart}


def primed_complete(s: dict, priming: int = PRIMING) -> bool:
    p = s.get("primed") or []
    return len(p) == priming and all((x.get("settled") or {}).get(k) for x in p for k in ("summary", "quiet", "logout")) \
        and all((x.get("quiescence") or {}).get("reached") for x in p)


def stats(samples: list[dict]) -> dict:
    out = {}
    for key in ("nav_to_summary_ms", "submit_to_summary_ms", "nav_to_login_box_ms"):
        values = [s[key] for s in samples if s[key] is not None]
        out[key] = {"median": statistics.median(values), "min": min(values), "max": max(values), "n": len(values)} if values else None
    out["clock_error_ms"] = max((s["clock_error_ms"] for s in samples), default=None)
    return out


def accounting_check(cold: list[dict], warm: list[dict]) -> dict:
    """§2.7: the byte accounting checked on one worker transfer that spans a
    cutoff and on one warm revalidation, before it is trusted."""
    spanning = next(({"url": r["url"], "observed_by_summary": r.get("observed_by_summary"), "encoded": r["encoded"],
                      "partial_at_login_box": r.get("partial_at_login_box")}
                     for s in cold for r in s["requests"] if r["worker"] and (r.get("partial_at_login_box") or r.get("partial_at_summary"))), None)
    reval = next(({"url": r["url"], "wire_status": r["wire_status"], "encoded": r["encoded"], "size": r["content_length"] or "size unknown"}
                  for s in warm for r in s["requests"] if r["cache"] == "304"), None)
    redirect = next(({"url": r["url"], "status": r["status"], "encoded": r["encoded"]}
                     for s in cold + warm for r in s["requests"] if str(r["cache"]).startswith("redirect")), None)
    return {"worker_transfer_spanning_a_cutoff": spanning or "none observed", "warm_revalidation": reval or "none observed",
            "redirect": redirect or "none observed",
            "mismatches": sorted({u for s in cold + warm for u in s["accounting_mismatches"]}),
            "unreconciled": sorted({f for s in cold + warm for f in s["reconciliation"]})}


def run(artifact: pathlib.Path, expected: list[list[str]], out: pathlib.Path, *, cold: int = COLD, warm: int = WARM) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    cold_s = [sample(journey(artifact, expected, 0, out / f"cold{i}.json")) for i in range(cold)]
    warm_s = [sample(journey(artifact, expected, PRIMING, out / f"warm{i}.json")) for i in range(warm)]
    result = {"cold": {**stats(cold_s), "samples": [_brief(s) for s in cold_s]},
              "warm": {**series(warm_s), "samples": [_brief(s) for s in warm_s], "condition": f"{PRIMING} standard priming journeys"},
              "accounting": accounting_check(cold_s, warm_s),
              "local_files": local_files(artifact)}
    (out / "samples.json").write_text(json.dumps({"cold": cold_s, "warm": warm_s}, indent=1) + "\n", encoding="utf-8")
    (out / "measures.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def _brief(s: dict) -> dict:
    return {k: s[k] for k in ("error", "nav_to_login_box_ms", "nav_to_summary_ms", "submit_to_summary_ms", "clock_error_ms", "bytes",
                              "by_origin", "trace_lost", "cache_evidence", "primed")} | {"served_from_cache": len(s["served_from_cache"])}


# --- what needs no browser ---------------------------------------------------------------


def local_files(artifact: pathlib.Path) -> dict:
    files = trees.files(trees.real_root(artifact))
    rows = {rel: {"raw": len(d), "brotli": len(brotli.compress(d, quality=11))} for rel, d in sorted(files.items())}
    return {"files": len(rows), "raw": sum(r["raw"] for r in rows.values()), "brotli": sum(r["brotli"] for r in rows.values()), "by_file": rows}


#: Lines we wrote, by role (§6): the report's declaration, the glue, and configuration.
ROLES = {
    "own": {"declaration": ("p01.report.json",), "glue": ("page.mjs", "report.mjs", "arrow.mjs", "source.package.mjs", "index.html", "page.css"),
            "configuration": ("build.py", "cdn.json")},
    "evidence": {"declaration": ("encrypted/pages/index.md",), "glue": ("encrypted/components/Login.svelte", "encrypted/components/Controls.svelte",
                                                                       "encrypted/components/session.js"),
                 "configuration": ("package.json", "evidence.config.yaml", "vite.bice.mjs", "pinned-engine.mjs", "trimmed-icons.mjs",
                                   "cdn.json", "extensions.json", ".npmrc")},
}


def lines(candidate: str, commit: str = "HEAD") -> dict:
    out = {}
    for role, names in ROLES[candidate].items():
        per = {}
        for name in names:
            try:
                text = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:prototypes/framework/{candidate}/{name}"],
                                      check=True, capture_output=True, text=True).stdout
            except subprocess.CalledProcessError:
                continue
            per[name] = sum(1 for line in text.splitlines() if line.strip())
        out[role] = {"files": per, "lines": sum(per.values())}
    out["total"] = sum(v["lines"] for v in out.values())
    return out


def gate_lists(candidate: str) -> dict:
    def count(name: str) -> int:
        return sum(1 for line in (HERE / "lists" / candidate / name).read_text(encoding="utf-8").splitlines()
                   if line.strip() and not line.strip().startswith("#"))
    return {"include_lines": count("include.txt"), "media_types": count("media_types.txt")}


def dependencies(candidate: str, entry: dict, runs: pathlib.Path) -> dict:
    if candidate == "own":
        cdn = json.loads((HERE / "own" / "cdn.json").read_text(encoding="utf-8"))["files"]
        return {"npm_packages": 0, "third_party_files": len(cdn), "third_party_bytes": sum(f.get("bytes", 0) for f in cdn)}
    lock = json.loads((HERE / "evidence" / "package-lock.json").read_text(encoding="utf-8"))
    kept = runs / candidate / entry["id"] / "node_modules"
    size = sum(p.stat().st_size for p in kept.rglob("*") if p.is_file() and not p.is_symlink()) if kept.is_dir() else None
    scripts = sorted(k for k, v in lock.get("packages", {}).items() if v.get("hasInstallScript"))
    return {"npm_packages": sum(1 for k in lock.get("packages", {}) if k), "node_modules_bytes": size,
            "fetch": entry.get("fetch"), "install": entry.get("install"), "scripts_run": [],
            "packages_with_install_scripts_not_run": scripts}


def build_measures(entry: dict, builder: pathlib.Path) -> dict:
    files = trees.files(trees.real_root(builder))
    return {"seconds": entry.get("seconds"), "files": len(files), "bytes": sum(len(d) for d in files.values()),
            "engine_in_build": any(rel.endswith(".wasm") or b"duckdb_web_" in d for rel, d in files.items())}


#: The packages each candidate depends on most, for upkeep: the framework, or the libraries.
UPKEEP = {"own": ("@duckdb/duckdb-wasm", "vega", "vega-lite", "apache-arrow"), "evidence": ("@evidence-dev/evidence", "@evidence-dev/core-components")}


def upkeep(candidate: str) -> dict:
    """The latest release of each, its date and its licence, from the npm
    registry — public metadata, fetched by the harness."""
    out = {}
    for name in UPKEEP[candidate]:
        try:
            with urllib.request.urlopen(f"https://registry.npmjs.org/{name.replace('/', '%2F')}", timeout=30) as r:
                meta = json.load(r)
            latest = meta["dist-tags"]["latest"]
            out[name] = {"latest": latest, "date": meta["time"].get(latest), "license": meta["versions"][latest].get("license")}
        except Exception as error:  # noqa: BLE001 — a measure not taken is recorded as such
            out[name] = {"error": f"{type(error).__name__}: {error}"}
    return out
