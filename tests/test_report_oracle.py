"""Check 4 of the report page: N96's browser oracle, judged (docs/report_page.md §4).

Stage 2.3 measured what each candidate does in the browser and reported it
(`docs/framework_prototype.md` §2.5.3). Here the same journey and collectors —
2.3's own driver, `prototypes/framework/browser/diagnostic.mjs`, its hooks in
every realm the DevTools protocol reaches, workers included — run on the P01
page over the invented package, and these are judged:

- no WebCrypto derivation, unwrap or decrypt outside a login attempt, and none
  that succeeds in the wrong password's attempt;
- no write to any store — Web Storage, IndexedDB, CacheStorage, the origin
  private file system, cookies, a service worker, history or navigation state;
- after logout, every worker that lived before it has ended, and the history's
  way back shows no report;
- nothing the browser can still read at the end holds a value of the package.

Reported, not judged, as in 2.3: the profile's bytes on disk after Chrome
closes, searched for the invented package's texts, which no page or library
carries — a hit names its file.

Not in `make check` (N119): it runs with `BICE_ORACLE=1`, before each PR and
against each preview, whose URL `BICE_ORACLE_URL` gives:

    BICE_ORACLE=1 uv run --frozen pytest -q -s -p no:cacheprovider tests/test_report_oracle.py
"""

from __future__ import annotations

import base64
import functools
import http.server
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading

import pytest

from bi_como_codigo import contract as c, release as r

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import site_fixture as sf  # noqa: E402
import test_report_page as page  # noqa: E402

DRIVER = ROOT / "prototypes" / "framework" / "browser" / "diagnostic.mjs"
CRYPTO = {"deriveKey", "deriveBits", "unwrapKey", "decrypt"}

pytestmark = pytest.mark.skipif(os.environ.get("BICE_ORACLE") != "1", reason="check 4 runs with BICE_ORACLE=1 (N119)")


def needles() -> list[bytes]:
    """The invented P01's values, as the gate spells them (§6 of the package gate)."""
    contract, _ = c.load(ROOT)
    values = c.Values("P01", b"\x00")
    report = contract.reports["P01"]
    for row in sf.ROWS["P01"]:
        for col, value in zip(report.columns, row):
            text = f"{value:f}" if hasattr(value, "as_tuple") else str(value)
            (values.numbers if col.numeric else values.texts).add(text)
    return [n for code, n in c.needles([values], set()) if code == c.CLEAR_VALUE]  # the totals object is a placeholder here


@pytest.fixture(scope="module")
def raw(tmp_path_factory):
    chrome = os.environ.get("BICE_CHROME") or shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome or not shutil.which("node"):
        pytest.fail("check 4 needs Chrome and Node")
    cache = page._cdn_cache()
    pins = json.loads(page.CDN.read_text(encoding="utf-8"))["files"]
    work = tmp_path_factory.mktemp("oracle")
    server = None
    url = os.environ.get("BICE_ORACLE_URL")
    if not url:
        deploy = work / "deploy"
        r.build(ROOT, deploy)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(page._Handler, directory=str(deploy)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}/relatorios/p01.html"
    password = next(p.password for p in r.profiles(ROOT) if p.id == page.DECLARATION["profile"])
    config = {
        "url": url, "out": str(work / "out"), "profile": str(work / "profile"), "password": password,
        "wrong": "nao-e-a-senha", "chrome": chrome,
        "fulfill": {pin["url"]: base64.b64encode((cache / pin["sha256"]).read_bytes()).decode() for pin in pins},
    }
    (work / "config.json").write_text(json.dumps(config))
    try:
        run = subprocess.run(["node", str(DRIVER), str(work / "config.json")], capture_output=True, text=True, timeout=600)
    finally:
        if server:
            server.shutdown()
    assert run.returncode == 0, run.stderr[-3000:]
    out = json.loads((work / "out" / "raw.json").read_text(encoding="utf-8"))
    out["_profile"] = str(work / "profile")
    return out


def _marks(raw) -> dict[str, list[float]]:
    """The journey's boundaries, as the hooks saw them at the events: each
    submission and the logout click; and the driver's own mark of the end."""
    out = {"submit": [], "logout": [], "enumerate": []}
    for e in raw["events"]:
        if e["kind"] == "mark":
            out[e["mark"]].append(e["t"])
    out["enumerate"] = [m["t"] for m in raw["marks"] if m["mark"] == "enumerate"]
    return out


def test_the_journey_ran(raw):
    assert raw["errors"] == []
    j = raw["journey"]
    assert j["loginBox"] and j["wrongShown"] and j["summary"] and j["ready"] and j["newLogin"]
    assert j["filters"] == len(page.CHANNELS) + 1 and not j["summaryAfterLogout"]
    assert any(e["kind"] == "installed" for e in raw["events"]), "no realm was instrumented"


def test_no_decryption_outside_an_attempt_and_none_in_the_wrong_one(raw):
    marks = _marks(raw)
    assert len(marks["submit"]) == 2 and len(marks["logout"]) == 1
    wrong, right, logout = marks["submit"][0], marks["submit"][1], marks["logout"][0]
    starts = {(e["doc"], e["id"]): e for e in raw["events"] if e["kind"] == "crypto" and e["phase"] == "start"}
    outcome = {(e["doc"], e["id"]): e["phase"] for e in raw["events"] if e["kind"] == "crypto" and e["phase"] != "start"}
    assert starts, "no WebCrypto call was seen: the hooks did not reach the reader"
    outside, in_wrong = [], []
    for key, call in starts.items():
        if call["t"] < wrong or call["t"] >= logout:
            outside.append(call["method"])
        elif call["t"] < right:
            in_wrong.append((call["method"], outcome.get(key)))
    assert outside == []
    assert all(method in ("deriveKey", "deriveBits") or (method == "unwrapKey" and result == "fail") for method, result in in_wrong), in_wrong
    assert not any(method in ("unwrapKey", "decrypt") and result == "ok" for method, result in in_wrong)


def test_nothing_is_written_to_any_store(raw):
    end = _marks(raw)["enumerate"][0]
    attempts = [e for e in raw["events"] if e["kind"] == "store" and e["t"] < end]
    committed = [w for w in raw["committed"] if w["t"] < end]
    assert attempts == [] and committed == []


def test_logout_ends_every_worker_of_the_session(raw):
    logout = _marks(raw)["logout"][0] / 1000  # the targets' times are the driver's wall clock, in ms since the epoch
    workers = [t for t in raw["targets"].values() if t["type"] in ("worker", "shared_worker", "service_worker")]
    assert workers, "no worker was attached: the engine's worker was not observed"
    before = [t for t in workers if t["attached"] / 1000 < logout]
    assert before and all(t.get("detached") for t in before), before
    alive = {t["id"] for t in raw["end"]["targets"] if t["type"] in ("worker", "shared_worker", "service_worker")}
    assert all(t["attached"] / 1000 >= logout for tid, t in raw["targets"].items() if tid in alive)
    assert not raw["end"]["afterBack"].get("summary")


def test_nothing_readable_at_the_end_holds_a_value(raw):
    readable = json.dumps(raw["end"]["readable"], ensure_ascii=False) + json.dumps(raw["end"]["cookies"], ensure_ascii=False)
    blob = readable.encode("utf-8")
    found = [n.decode("utf-8") for n in needles() if c.found(n, blob)]
    assert found == []
    assert raw["end"]["readable"]["unobserved"] == [], raw["end"]["readable"]["unobserved"]


def test_the_disk_after_close_is_reported(raw):
    """Reported, not judged: files of the closed profile holding a text of the
    invented package — texts no page or library carries."""
    texts = [n for n in needles() if not n[:1].isdigit() and not n[:1] == b"-"]
    hits = {}
    for path in pathlib.Path(raw["_profile"]).rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            count = sum(1 for n in texts if n in data)
            if count:
                hits[str(path.relative_to(raw["_profile"]))] = count
    print(f"\ncheck 4, disk after close: {len(hits)} file(s) hold a text of the invented package" + "".join(f"\n  {k}: {v}" for k, v in sorted(hits.items())))
