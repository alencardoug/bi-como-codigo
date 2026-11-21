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
import trees

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
        for name, part in (("written", self.written), ("committed", self.written.get("committed", {})), ("readable", self.readable),
                           ("on disk", self.on_disk), ("fetched", self.fetches)):
            out += [f"{name}: {f['code']}" for f in part.get("findings", [])]
        out += [s["code"] for s in self.survives]
        return out

    def record(self) -> dict:
        return dataclasses.asdict(self)


# --- when it decrypts -------------------------------------------------------------------


def journey_marks(events: list[dict], driver_marks: list[dict]) -> tuple[list[dict], list[dict]]:
    """The submissions and the logout, as the page's own hooks saw them at the
    events (PROTO-1-11); the driver's marks only where the page's are missing,
    said so."""
    page = sorted((e for e in events if e["kind"] == "mark" and e["targetType"] == "page"), key=lambda e: e["t"])
    if page:
        return [{"mark": e["mark"], "t": e["t"], "doc": e["doc"]} for e in page], []
    return ([{"mark": m["mark"], "t": m["t"], "doc": None} for m in driver_marks if m["mark"] in ("submit", "logout")],
            [{"what": "journey marks", "why": "the page's hooks marked no submission or logout; the driver's marks stand in"}])


def attempts(marks: list[dict]) -> list[tuple[float, float, str]]:
    """(opens, closes, which): an attempt opens at a submission and closes at
    the next submission or at logout; the journey submits the wrong password,
    then the right one."""
    out = []
    submits = [m["t"] for m in marks if m["mark"] == "submit"]
    logout = next((m["t"] for m in marks if m["mark"] == "logout"), float("inf"))
    submits = [t for t in submits if t < logout]
    for n, t in enumerate(submits):
        closes = submits[n + 1] if n + 1 < len(submits) else logout
        out.append((t, closes, "wrong" if n == 0 else "right"))
    return out


def decrypt_calls(events: list[dict], marks: list[dict]) -> list[dict]:
    """Each call attributed to the attempt open when it started — a call in
    flight at logout keeps it (FPROTO-8-05). After logout, the document a call
    ran in says where: the session's own document, a worker of the session, or
    the new page (PROTO-1-11)."""
    windows = attempts(marks)
    logout = next((m for m in marks if m["mark"] == "logout"), None)
    first = windows[0][0] if windows else float("inf")
    starts = {(e["target"], e["doc"], e["id"]): e for e in events if e["kind"] == "crypto" and e["phase"] == "start"}
    ends = {(e["target"], e["doc"], e["id"]): e["phase"] for e in events if e["kind"] == "crypto" and e["phase"] != "start"}
    out = []
    for key, e in sorted(starts.items(), key=lambda kv: kv[1]["t"]):
        outcome = ends.get(key, "unfinished")
        attempt = next((w for w in windows if w[0] <= e["t"] < w[1]), None)
        rec = {"method": e["method"], "realm": e["realm"], "target_type": e["targetType"], "t": e["t"], "outcome": outcome}
        if attempt is None:
            if e["t"] < first:
                when = "before any submission"
            elif logout is not None and e["doc"] == logout["doc"]:
                when = "after logout in the session's own document"
            elif e["targetType"] == "page":
                when = "on the new page before a new submission"
            else:
                when = "after logout in a target of the session"
            rec |= {"code": PREMATURE_DECRYPT, "when": when}
        elif attempt[2] == "wrong":
            bad = (e["method"] == "unwrapKey" and outcome == "ok") or e["method"] == "decrypt"
            rec |= {"code": UNEXPECTED_DECRYPT if bad else "expected", "attempt": "wrong"}
        else:
            rec |= {"code": "expected", "attempt": "right"}
        out.append(rec)
    return out


def unacknowledged(raw: dict) -> list[dict]:
    """A realm the driver attached whose hooks never said they were installed:
    nothing of it was observed (PROTO-1-12)."""
    installed = {e["target"] for e in raw["events"] if e["kind"] == "installed"}
    out = []
    for target, t in raw["targets"].items():
        if t["type"] in {"page", "iframe", "worker", "shared_worker", "service_worker"} and target not in installed \
                and not str(t.get("url", "")).startswith("about:"):
            out.append({"what": "hooks", "target": t["type"], "url": t.get("url"), "why": "no acknowledgement from this realm"})
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


def written(events: list[dict], marks: list[dict], committed: list[dict], needles, *, until_wall: float | None = None) -> dict:
    """What the collectors saw during the journey — until the diagnostic's own
    enumeration of the stores begins —, kept apart: the hooks' write attempts,
    each value as the browser stored it, and the writes the protocol reports
    as committed, a transient property write among them (PROTO-1-12)."""
    items, entry_points, unobserved = [], [], []
    until = next((m["t"] for m in marks if m["mark"] == "enumerate"), float("inf"))
    for n, e in enumerate(x for x in events if x["kind"] == "store" and x["t"] < until):
        entry_points.append({"store": e["store"], "op": e["op"], "target_type": e["targetType"]})
        value = e.get("value") or {}
        if value.get("unreadable"):
            unobserved.append({"what": f"{e['store']}.{e['op']}", "why": value["unreadable"]})
        data = _value_bytes(value)
        if data is not None:
            items.append(io_.Item(f"write#{n}:{e['store']}.{e['op']}", data, role=io_.COLLECTED))
        if isinstance(e.get("key"), str) and e["store"] in {"history", "navigation"}:
            items.append(io_.Item(f"write#{n}:{e['store']}.url", e["key"].encode(), role=io_.COLLECTED))
    attempts_report = _inspect(items, needles)
    done, changes = [], []
    for n, w in enumerate(x for x in committed if until_wall is None or x["t"] < until_wall):
        if w.get("value") is not None:
            done.append(io_.Item(f"committed#{n}:{w['store']}.{w['key']}", f"{w['key']}={w['value']}".encode(), role=io_.COLLECTED))
        else:
            changes.append({"store": w["store"], "op": w["op"], "name": w.get("key")})
    return attempts_report | {"entry_points": entry_points, "committed": _inspect(done, needles), "content_changes": changes,
                              "unobserved": unobserved}


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


def _without_known_bodies(data: bytes, bodies: list[bytes]) -> tuple[bytes, int]:
    """An HTTP or script cache entry holds a response body beside its key and
    headers: a body that is a file of the artifact or a pinned third-party body
    is recognised and taken out, and the rest is inspected."""
    found = 0
    for body in bodies:
        if len(body) >= 64 and body in data:
            data = data.replace(body, b"")
            found += 1
    return data, found


def on_disk(profile: pathlib.Path, needles, *, known: set[str], bodies: list[bytes] = ()) -> dict:
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
        if "Cache_Data" in rel or "ScriptCache" in rel or "Code Cache" in rel:
            data, recognised = _without_known_bodies(data, list(bodies))
            if recognised:
                coverage["cache entries with a known body taken out"] = coverage.get("cache entries with a known body taken out", 0) + 1
        items.append(io_.Item(rel, data, role=io_.COLLECTED))
        coverage["bytes"] = coverage.get("bytes", 0) + 1
    report = io_.inspect_items(items, needles)
    rec = report.record()
    rec["inconclusive"] = [n for n in rec["inconclusive"]]  # Chrome's own binaries: listed, not hidden
    return rec | {"coverage": coverage, "not_scanned_files": not_scanned, "unobserved": unobserved, "files": files_by_format}


# --- the whole diagnostic -----------------------------------------------------------------


_BASELINE: dict[str, frozenset[str]] = {}


def baseline(chrome: str | None = None, seconds: float = 6) -> frozenset[str]:
    """The digests of every file of a pristine profile of the same Chrome, on
    `about:blank` with no page of ours: what Chrome writes on its own — its
    built-in extensions' scripts among them — is recognised in a journey's
    profile, so that it is never read as the candidate's."""
    binary = chrome or "google-chrome"
    if binary not in _BASELINE:
        with tempfile.TemporaryDirectory(prefix="bice-baseline-") as tmp:
            proc = subprocess.Popen([binary, "--headless=new", "--no-first-run", "--no-default-browser-check",
                                     "--disable-background-networking", "--disable-component-update", "--disable-sync",
                                     f"--user-data-dir={tmp}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                proc.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=10)
            _BASELINE[binary] = frozenset(x.digest for x in trees.entries(pathlib.Path(tmp)) if x.kind == "file")
    return _BASELINE[binary]


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
    artifact_digests = {x.rel: x.digest for x in trees.entries(trees.real_root(artifact)) if x.kind == "file"}  # no link followed
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
        known = set(artifact_digests.values()) | set((cdn or {}).values()) | set(baseline(chrome))
        bodies = [x for x in trees.files(trees.real_root(artifact)).values()] + list((fulfill or {}).values())
        disk = on_disk(profile, needles, known=known, bodies=bodies)
    marks, mark_gaps = journey_marks(raw["events"], raw["marks"])
    return Diagnosis(
        decrypt=decrypt_calls(raw["events"], marks),
        written=written(raw["events"], raw["marks"], raw.get("committed", []), needles,
                        until_wall=next((m["t"] for m in raw["marks"] if m["mark"] == "enumerate"), None)),
        readable=readable(raw["end"], needles),
        on_disk=disk,
        survives=survival(raw),
        fetches=fetched(raw, out, server.url, artifact_digests, needles, cdn=cdn or {}, validated=validated or {}),
        unobserved=raw["unobserved"] + mark_gaps + unacknowledged(raw) + [{"what": "driver error", "why": e} for e in raw["errors"]]
        + [{"what": "known gap", "why": g} for g in (
            "a write created and removed during the journey that no collector saw",
            "a fragment change of the URL",
            "an origin private file system bucket opened by name",
            "integers inside V8-serialized IndexedDB values on disk")],
        journey=raw.get("journey", {}),
    )
