"""The browser diagnostic of stage 2.3 (docs/framework_prototype.md §2.5.3).

Serves an artifact on 127.0.0.1, runs the driver (`browser/diagnostic.mjs`)
on a fresh Chrome profile, and reads what it observed: when the page
decrypted, against the journey's attempts; what it stored, through the
carrier inspection as data-bearing carriers; what persists, as three kinds of
evidence never merged — written during the journey, readable by the browser
at the end, bytes on disk after close —; what survives logout; and what it
fetched. Each part says what it could not observe. It is measured and
reported, never part of the verdict (N96).
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import tempfile

import inspect_output as io_
import leveldb
import serve

HERE = pathlib.Path(__file__).resolve().parent
DRIVER = HERE / "browser" / "diagnostic.mjs"
PASSWORD = "senha_complexa_123"
WRONG = "senha_errada_000"

PREMATURE_DECRYPT = "PREMATURE_DECRYPT"
UNEXPECTED_DECRYPT = "UNEXPECTED_DECRYPT"
SESSION_SURVIVES = "SESSION_SURVIVES"

#: The profile folders that hold a page's storage; the rest of a profile is
#: Chrome's own and is listed as not scanned.
STORAGE_DIRS = ("Local Storage", "Session Storage", "IndexedDB", "Service Worker", "File System", "Cache", "Code Cache",
                "Network", "WebStorage", "shared_proto_db", "blob_storage")


@dataclasses.dataclass
class Diagnosis:
    decrypt: list[dict]
    written: dict
    readable: dict
    on_disk: dict
    survives: list[dict]
    fetches: dict
    unobserved: list[dict]
    journey: dict

    def leads(self) -> list[str]:
        """What is reported first among a candidate's results (§2.5.3)."""
        out = [d["code"] for d in self.decrypt if d["code"] in {PREMATURE_DECRYPT, UNEXPECTED_DECRYPT}]
        for name, part in (("written", self.written), ("readable", self.readable), ("on disk", self.on_disk), ("fetched", self.fetches)):
            out += [f"{name}: {f['code']}" for f in part.get("findings", [])]
        out += [s["code"] for s in self.survives]
        return out

    def record(self) -> dict:
        return dataclasses.asdict(self)


# --- when it decrypts -------------------------------------------------------------------


def attempts(marks: list[dict]) -> list[tuple[float, float, str]]:
    """(opens, closes, which): an attempt opens at a submission and closes at
    the next submission or at logout; the journey submits the wrong password,
    then the right one."""
    out = []
    submits = [m["t"] for m in marks if m["mark"] == "submit"]
    logout = next((m["t"] for m in marks if m["mark"] == "logout"), float("inf"))
    for n, t in enumerate(submits):
        closes = submits[n + 1] if n + 1 < len(submits) else logout
        out.append((t, closes, "wrong" if n == 0 else "right"))
    return out


def decrypt_calls(events: list[dict], marks: list[dict]) -> list[dict]:
    """Each call attributed to the attempt open when it started — a call in
    flight at logout keeps it (FPROTO-8-05)."""
    windows = attempts(marks)
    logout = next((m["t"] for m in marks if m["mark"] == "logout"), float("inf"))
    first = windows[0][0] if windows else float("inf")
    starts = {(e["target"], e["doc"], e["id"]): e for e in events if e["kind"] == "crypto" and e["phase"] == "start"}
    ends = {(e["target"], e["doc"], e["id"]): e["phase"] for e in events if e["kind"] == "crypto" and e["phase"] != "start"}
    out = []
    for key, e in sorted(starts.items(), key=lambda kv: kv[1]["t"]):
        outcome = ends.get(key, "unfinished")
        attempt = next((w for w in windows if w[0] <= e["t"] < w[1]), None)
        rec = {"method": e["method"], "realm": e["realm"], "target_type": e["targetType"], "t": e["t"], "outcome": outcome}
        if attempt is None:
            when = ("before any submission" if e["t"] < first else
                    "on the new page before a new submission" if e["targetType"] == "page" else "after logout in a target of the session")
            rec |= {"code": PREMATURE_DECRYPT, "when": when}
        elif attempt[2] == "wrong":
            bad = (e["method"] == "unwrapKey" and outcome == "ok") or e["method"] == "decrypt"
            rec |= {"code": UNEXPECTED_DECRYPT if bad else "expected", "attempt": "wrong"}
        else:
            rec |= {"code": "expected", "attempt": "right"}
        out.append(rec)
    return out


# --- values as carriers -------------------------------------------------------------------


def _value_bytes(value: dict | None) -> bytes | None:
    if not value:
        return None
    if "b64" in value:
        return base64.b64decode(value["b64"])
    if "text" in value and value["text"] is not None:
        return value["text"].encode("utf-8", "surrogatepass")
    return None


def _inspect(items: list[io_.Item], needles, **kw) -> dict:
    report = io_.inspect_items(items, needles, **kw)
    return report.record() | {"carriers": len(items)}


def written(events: list[dict], marks: list[dict], needles) -> dict:
    """What the collectors saw during the journey — until the diagnostic's own
    enumeration of the stores begins."""
    items, entry_points = [], []
    until = next((m["t"] for m in marks if m["mark"] == "enumerate"), float("inf"))
    for n, e in enumerate(x for x in events if x["kind"] == "store" and x["t"] < until):
        entry_points.append({"store": e["store"], "op": e["op"], "target_type": e["targetType"]})
        data = _value_bytes(e.get("value"))
        if data is not None:
            items.append(io_.Item(f"write#{n}:{e['store']}.{e['op']}", data, role=io_.COLLECTED))
        if isinstance(e.get("key"), str) and e["store"] in {"history", "navigation"}:
            items.append(io_.Item(f"write#{n}:{e['store']}.url", e["key"].encode(), role=io_.COLLECTED))
    return _inspect(items, needles) | {"entry_points": entry_points}


def readable(end: dict, needles) -> dict:
    r = end.get("readable") or {}
    items = []
    for area in ("localStorage", "sessionStorage"):
        for k, v in (r.get(area) or {}).items():
            items.append(io_.Item(f"{area}:{k}", f"{k}={v}".encode(), role=io_.COLLECTED))
    for db, stores in (r.get("indexedDB") or {}).items():
        for store, values in stores.items():
            for n, v in enumerate(values):
                items.append(io_.Item(f"indexedDB:{db}/{store}#{n}", v.encode(), role=io_.COLLECTED))
    for name, entries in (r.get("caches") or {}).items():
        for url, b64 in entries.items():
            items.append(io_.Item(f"caches:{name}:{url}", base64.b64decode(b64), role=io_.COLLECTED, url=url))
    for name, b64 in (r.get("opfs") or {}).items():
        items.append(io_.Item(f"opfs:{name}", base64.b64decode(b64), role=io_.COLLECTED))
    for c in end.get("cookies") or []:
        items.append(io_.Item(f"cookie:{c['name']}", f"{c['name']}={c['value']}".encode(), role=io_.COLLECTED))
    return _inspect(items, needles) | {"service_workers": r.get("serviceWorkers", []), "unobserved": r.get("unobserved", [])}


def fetched(raw: dict, out: pathlib.Path, origin: str, artifact_digests: dict[str, str], needles, *, cdn, validated) -> dict:
    """Every effective body the protocol returned; the envelope and the
    artifact's own files recognised by origin, path and digest."""
    items, recorded, unobserved = [], [], []
    for req in raw["requests"].values():
        url = req.get("url", "")
        if not url.startswith(("http:", "https:")):
            continue
        if not req.get("body"):
            unobserved.append({"url": url, "status": req.get("status"), "why": req.get("failed") or "no body returned"})
            continue
        data = (out / "bodies" / req["body"]).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if url.startswith(origin):
            rel = url[len(origin):].split("?")[0].split("#")[0] or "index.html"
            if rel.startswith("package/"):
                items.append(io_.Item(rel, data))
                continue
            if artifact_digests.get(rel) == digest:
                recorded.append({"url": url, "why": "the artifact's own file"})
                continue
        items.append(io_.Item(f"fetch:{url}", data, role=io_.COLLECTED, url=url))
    return _inspect(items, needles, cdn=cdn, validated=validated) | {"recognised": recorded, "unobserved": unobserved}


# --- bytes on disk after close ------------------------------------------------------------


def _sqlite_items(path: pathlib.Path) -> tuple[list[io_.Item], list[dict]]:
    items, unobserved = [], []
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            columns = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
            for n, row in enumerate(con.execute(f'SELECT * FROM "{table}"')):
                for col, v in zip(columns, row):
                    if col == "encrypted_value":
                        if v:
                            unobserved.append({"file": str(path.name), "field": f"{table}.{col}", "why": "kept encrypted by Chromium"})
                        continue
                    if isinstance(v, str):
                        v = v.encode()
                    if isinstance(v, bytes) and v:
                        items.append(io_.Item(f"{path.name}:{table}#{n}.{col}", v, role=io_.COLLECTED))
    finally:
        con.close()
    return items, unobserved


def _utf16(data: bytes) -> bytes | None:
    """V8 keeps a two-byte string as UTF-16LE: given back as UTF-8 for the search."""
    if data.count(b"\x00") * 3 < len(data):
        return None
    return data.decode("utf-16-le", "ignore").encode("utf-8")


def on_disk(profile: pathlib.Path, needles, *, known: set[str]) -> dict:
    """The profile directory, read by format: LevelDB with its Snappy blocks,
    SQLite, and the rest as bytes; files recognised by digest are recorded.
    Coverage is per format and per field."""
    items, unobserved, coverage, not_scanned, files_by_format = [], [], {}, 0, {}
    for path in sorted(p for p in profile.rglob("*") if p.is_file() and not p.is_symlink()):
        rel = path.relative_to(profile).as_posix()
        if not any(part in STORAGE_DIRS for part in path.relative_to(profile).parts) and path.name != "Cookies":
            not_scanned += 1
            continue
        if path.name in ("LOG", "LOG.old", "LOCK", "CURRENT") or path.name.startswith("MANIFEST-"):
            coverage["LevelDB bookkeeping, not data"] = coverage.get("LevelDB bookkeeping, not data", 0) + 1
            continue
        data = path.read_bytes()
        files_by_format.setdefault("all", []).append(rel)
        if hashlib.sha256(data).hexdigest() in known:
            coverage["recognised by digest"] = coverage.get("recognised by digest", 0) + 1
            continue
        if path.suffix in (".log", ".ldb") and "leveldb" in rel.lower() or path.parent.name.endswith(".leveldb"):
            try:
                for n, (k, v) in enumerate(leveldb.read(path)):
                    for name, blob in (("key", k), ("value", v)):
                        if blob:
                            items.append(io_.Item(f"{rel}#{n}.{name}", blob, role=io_.COLLECTED))
                            wide = _utf16(blob)
                            if wide:
                                items.append(io_.Item(f"{rel}#{n}.{name} > utf16", wide, role=io_.COLLECTED))
                coverage["leveldb"] = coverage.get("leveldb", 0) + 1
            except (leveldb.Unreadable, IndexError, ValueError) as error:
                unobserved.append({"file": rel, "why": f"LevelDB unreadable: {error}"})
            continue
        if data[:16] == b"SQLite format 3\x00":
            try:
                got, missing = _sqlite_items(path)
                items += got
                unobserved += missing
                coverage["sqlite"] = coverage.get("sqlite", 0) + 1
                files_by_format.setdefault("sqlite", []).append(rel)
            except sqlite3.Error as error:
                unobserved.append({"file": rel, "why": f"SQLite unreadable: {error}"})
            continue
        items.append(io_.Item(rel, data, role=io_.COLLECTED))
        coverage["bytes"] = coverage.get("bytes", 0) + 1
    report = io_.inspect_items(items, needles)
    rec = report.record()
    rec["inconclusive"] = [n for n in rec["inconclusive"]]  # Chrome's own binaries: listed, not hidden
    return rec | {"coverage": coverage, "not_scanned_files": not_scanned, "unobserved": unobserved, "files": files_by_format}


# --- the whole diagnostic -----------------------------------------------------------------


def low_port() -> int:
    """A free port below 10,000: never a count needle, which all have five
    digits or more (§2.1), so the origin itself is no lead."""
    import random
    import socket

    for port in random.sample(range(2000, 10_000), 200):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("no free port below 10,000")


def survival(raw: dict) -> list[dict]:
    out = []
    created = sum(1 for e in raw["events"] if e["kind"] == "worker" and e["op"] == "create")
    terminated = sum(1 for e in raw["events"] if e["kind"] == "worker" and e["op"] == "terminate")
    alive = [t for t in raw["end"].get("targets", []) if t["type"] in {"worker", "shared_worker", "service_worker"}
             and not t["url"].startswith(("chrome:", "chrome-extension:", "devtools:"))]
    if alive:
        out.append({"code": SESSION_SURVIVES, "what": "workers alive after logout", "count": len(alive), "created": created, "terminated": terminated})
    if raw["end"].get("historyAfterLogout", 1) > raw["end"].get("historyAtStart", 1):
        out.append({"code": SESSION_SURVIVES, "what": "history entries after logout", "count": raw["end"]["historyAfterLogout"]})
    if (raw["end"].get("afterBack") or {}).get("summary") or raw.get("journey", {}).get("summaryAfterLogout"):
        out.append({"code": SESSION_SURVIVES, "what": "the summary reachable after logout"})
    return out


def run(artifact: pathlib.Path, needles: io_.Needles, *, out: pathlib.Path, query: str = "", cdn: dict[str, str] | None = None,
        fulfill: dict[str, bytes] | None = None, validated: dict[str, str] | None = None, chrome: str | None = None,
        timeout: float = 600) -> Diagnosis:
    """One journey on one fresh profile, used for this journey only."""
    out.mkdir(parents=True, exist_ok=False)
    artifact_digests = {p.relative_to(artifact).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in artifact.rglob("*") if p.is_file()}
    with tempfile.TemporaryDirectory(prefix="bice-profile-") as tmp, serve.Server(artifact, port=low_port()) as server:
        profile = pathlib.Path(tmp) / "profile"
        config = {"url": server.url + query, "out": str(out), "profile": str(profile), "password": PASSWORD, "wrong": WRONG,
                  **({"chrome": chrome} if chrome else {}),
                  **({"fulfill": {u: base64.b64encode(b).decode() for u, b in fulfill.items()}} if fulfill else {})}
        (out / "config.json").write_text(json.dumps(config))
        result = subprocess.run(["node", str(DRIVER), str(out / "config.json")], capture_output=True, timeout=timeout)
        if result.returncode != 0 or not (out / "raw.json").exists():
            raise RuntimeError(f"the driver failed: {result.stderr.decode(errors='replace')[-3000:]}")
        raw = json.loads((out / "raw.json").read_text())
        known = set(artifact_digests.values()) | set((cdn or {}).values())
        disk = on_disk(profile, needles, known=known)
    return Diagnosis(
        decrypt=decrypt_calls(raw["events"], raw["marks"]),
        written=written(raw["events"], raw["marks"], needles),
        readable=readable(raw["end"], needles),
        on_disk=disk,
        survives=survival(raw),
        fetches=fetched(raw, out, server.url, artifact_digests, needles, cdn=cdn or {}, validated=validated or {}),
        unobserved=raw["unobserved"] + [{"what": "driver error", "why": e} for e in raw["errors"]]
        + [{"what": "known gap", "why": g} for g in (
            "a write created and removed during the journey that no collector saw",
            "a fragment change of the URL",
            "an origin private file system bucket opened by name",
            "integers inside V8-serialized IndexedDB values on disk")],
        journey=raw.get("journey", {}),
    )
