"""The measures' accounting of §2.7, on synthetic journeys: the clock from
the protocol's pairs, bytes by cutoff with partial transfers labelled, the
cache evidence, and warm samples split into series by it — proved once on a
deliberately mismatched trace and once on an incomplete one."""

from __future__ import annotations

import shutil

import pytest

import measure


GOOD_PRIMER = {"settled": {"summary": True, "quiet": True, "logout": True}, "quiescence": {"reached": True}}


def _raw(*, wasm="wasm.StartStreamingCompilation", lost=False, cache=None, primed=None):
    """A page that requests a page and a worker's WASM, the WASM spanning the summary's cutoff."""
    t = 1000.0  # monotonic seconds; wall = t * 1000 + 5_000_000
    wall = lambda s: (s * 1000 + 5_000_000) / 1000  # noqa: E731 — the protocol's wallTime is seconds
    page = {"session": "P", "url": "http://127.0.0.1:1/", "status": 200, "wire_status": 200, "events": [
        {"e": "sent", "ts": t, "wall": wall(t)}, {"e": "data", "ts": t + 0.1, "encoded": 1000}], "finished": {"ts": t + 0.1, "encoded": 1000},
        **(cache or {})}
    engine = {"session": "W", "url": "https://cdn.jsdelivr.net/npm/x@1/e.wasm", "status": 200, "wire_status": 200, "events": [
        {"e": "sent", "ts": t + 0.2, "wall": wall(t + 0.2)}, {"e": "data", "ts": t + 0.5, "encoded": 4000},
        {"e": "data", "ts": t + 2.5, "encoded": 6000}], "finished": {"ts": t + 2.5, "encoded": 10000}}
    marks = [{"mark": "navigation", "t": t * 1000 + 5_000_000}, {"mark": "login_box", "t": t * 1000 + 5_000_300},
             {"mark": "submit", "t": t * 1000 + 5_000_301}, {"mark": "summary", "t": t * 1000 + 5_001_000}]
    return {"origin": "http://127.0.0.1:1", "primed": [GOOD_PRIMER, GOOD_PRIMER] if primed is None else primed, "measured": {
        "page": "P", "marks": marks, "requests": {"P:1": page, "W:1": engine},
        "sessions": {"P": [[t, wall(t)]], "W": [[t + 0.2, wall(t + 0.2)]]}, "trace": [{"name": w} for w in ([wasm] if isinstance(wasm, str) else wasm)],
        "trace_lost": lost}}


def test_marks_bytes_and_partial_transfers_by_cutoff():
    s = measure.sample(_raw())
    assert s["nav_to_summary_ms"] == 1000 and s["submit_to_summary_ms"] == 699 and s["clock_error_ms"] == 0
    assert s["bytes"]["summary"] == {"observed": 5000, "completed": 1000, "partial_requests": 1,
                                     "by_origin": {"local": 1000, "cdn.jsdelivr.net": 0},
                                     "observed_by_origin": {"local": 1000, "cdn.jsdelivr.net": 4000}}
    assert s["reconciliation"] == []
    engine = next(r for r in s["requests"] if r["worker"])
    assert engine["partial_at_summary"] and not engine["completed_by_summary"] and engine["encoded"] == 10000
    assert measure.accounting_check([s], [])["worker_transfer_spanning_a_cutoff"]["url"].endswith("e.wasm")


def test_a_revalidation_counts_its_wire_bytes_and_reports_the_body_apart():
    s = measure.sample(_raw(cache={"wire_status": 304, "status": 200, "content_length": "1457"}))
    assert s["served_from_cache"] == [{"url": "http://127.0.0.1:1/", "cache": "304", "size": "1457"}]
    assert measure.accounting_check([], [s])["warm_revalidation"]["wire_status"] == 304


def test_warm_samples_split_by_their_wasm_evidence_and_a_lost_trace_enters_no_series():
    same = [measure.sample(_raw()), measure.sample(_raw())]
    mismatched = measure.sample(_raw(wasm="wasm.DeserializeNativeModule"))  # equal HTTP and JS evidence, other WASM
    lost = measure.sample(_raw(lost=True))
    out = measure.series([*same, mismatched, lost])
    assert [g["samples"] for g in out["series"]] == [[0, 1], [2]] and out["apart"] == [3]
    assert [g["wasm"] for g in out["series"]] == ["compiled", "cached"]


def test_samples_served_on_different_ports_share_a_series():
    a, b = _raw(), _raw()
    for raw, port in ((a, "1"), (b, "2")):
        raw["origin"] = f"http://127.0.0.1:{port}"
        raw["measured"]["requests"]["P:1"]["url"] = f"http://127.0.0.1:{port}/"
    assert [g["samples"] for g in measure.series([measure.sample(a), measure.sample(b)])["series"]] == [[0, 1]]


def test_incomplete_priming_or_an_unclassifiable_engine_enters_no_series():
    """CMP-1-10: a failed primer — no summary, requests in flight, logout unconfirmed,
    no quiescence, or one primer only — and a trace with both a compiled and a
    deserialized module, which names neither, leave the sample apart."""
    failed = [{**GOOD_PRIMER, "settled": {**GOOD_PRIMER["settled"], k: False}} for k in ("summary", "quiet", "logout")]
    samples = [measure.sample(_raw())]
    samples += [measure.sample(_raw(primed=[GOOD_PRIMER, f])) for f in failed]
    samples += [measure.sample(_raw(primed=[GOOD_PRIMER, {**GOOD_PRIMER, "quiescence": {"reached": False}}])),
                measure.sample(_raw(primed=[GOOD_PRIMER])),
                measure.sample(_raw(wasm=["wasm.StartStreamingCompilation", "wasm.DeserializeNativeModule"]))]
    out = measure.series(samples)
    assert [g["samples"] for g in out["series"]] == [[0]] and out["apart"] == [1, 2, 3, 4, 5, 6]
    assert samples[6]["cache_evidence"]["wasm"] == "unclassified"


def test_a_redirect_keeps_each_hop_and_the_totals_reconcile():
    """CMP-1-11: a 302 then a 200 on one request id — both hops counted, each by its own time."""
    raw = _raw()
    page = raw["measured"]["requests"]["P:1"]
    page["hops"] = [{"url": "http://127.0.0.1:1/old", "status": 302, "encoded": 150, "ts": 1000.05}]
    s = measure.sample(raw)
    hop = next(r for r in s["requests"] if r["cache"] == "redirect 302")
    assert hop["url"] == "http://127.0.0.1:1/old" and hop["completed_by_summary"] and hop["encoded"] == 150
    assert s["bytes"]["summary"]["completed"] == 1150 and s["by_origin"]["local"] == {"requests": 2, "encoded": 1150}
    assert s["reconciliation"] == [] and measure.accounting_check([s], [])["redirect"]["status"] == 302
    broken = dict(s["bytes"]["summary"], completed=9999)
    assert "summary: completed by origin does not add up" in measure.reconcile({"summary": broken}, s["by_origin"], s["requests"])


# --- CMP-2-07: a worker's script, answered in the worker's session -------------------------


def test_an_answered_request_with_no_completion_has_its_bytes_unknown_not_reconciled():
    raw = _raw()
    raw["measured"]["requests"]["P:2"] = {"session": "P", "url": "http://127.0.0.1:1/worker.js", "status": 200, "wire_status": 200,
                                          "events": [{"e": "sent", "ts": 1000.2, "wall": 5000.2}]}
    s = measure.sample(raw)
    assert "bytes unknown: http://127.0.0.1:1/worker.js" in s["reconciliation"]


def test_an_event_of_another_session_is_on_that_sessions_clock():
    raw = _raw()
    raw["measured"]["sessions"]["W"] = [[2000.2, (1000.2 * 1000 + 5_000_000) / 1000]]  # W's clock runs 1000 s ahead
    engine = raw["measured"]["requests"]["W:1"]
    engine["session"] = "P"  # sent in the page's session, answered in the worker's
    engine["events"] = [engine["events"][0]] + [{**e, "ts": e["ts"] + 1000, "s": "W"} for e in engine["events"][1:]]
    engine["finished"] = {**engine["finished"], "ts": engine["finished"]["ts"] + 1000, "s": "W"}
    s = measure.sample(raw)
    assert s["bytes"]["summary"]["observed"] == 5000 and s["bytes"]["summary"]["partial_requests"] == 1


_WORKER_PAGE = """<!doctype html><meta charset="utf-8"><body>
<input data-bice="password" type="password"><button data-bice="submit">Entrar</button>
<script>
document.querySelector('[data-bice=submit]').onclick = () => {
  const blob = URL.createObjectURL(new Blob([`fetch('${location.origin}/stream.bin').then(r => r.arrayBuffer()).then(b => postMessage(b.byteLength));`]));
  const w = new Worker(__WORKER__);
  w.onmessage = (e) => {
    document.body.innerHTML = '<div data-bice="summary"><table><tr><td>2024-01</td><td>r</td><td>R$ 1,00</td><td>' + e.data + '</td></tr></table></div>'
      + '<button data-bice="logout" onclick="location.replace(location.href)">Sair</button>';
  };
};
</script>"""


@pytest.mark.skipif(not (shutil.which("node") and shutil.which("google-chrome")), reason="needs node and Chrome")
@pytest.mark.parametrize("worker", ["'worker.js'", "blob"])
def test_a_workers_bootstrap_completes_its_journey_with_its_bytes(tmp_path, worker):
    """CMP-2-07: an HTTP worker's script was sent in the page's session and finished in the
    worker's; the journey waited six minutes for it and then counted nothing. It is one request,
    and its bytes count; a blob worker's script is no network."""
    import os
    import time
    site = tmp_path / "site"
    site.mkdir()
    (site / "stream.bin").write_bytes(os.urandom(200_000))
    (site / "worker.js").write_text("fetch('stream.bin').then(r => r.arrayBuffer()).then(b => postMessage(b.byteLength));\n")
    (site / "index.html").write_text(_WORKER_PAGE.replace("__WORKER__", worker), encoding="utf-8")
    t0 = time.time()
    raw = measure.journey(site, [["2024-01", "r", "R$ 1,00", "200000"]], 1, tmp_path / "out.json", timeout=600)
    assert time.time() - t0 < 120 and raw["measured"]["settled"] == {"summary": True, "quiet": True}
    assert raw["primed"][0]["settled"]["quiet"]
    s = measure.sample(raw)
    assert s["reconciliation"] == [], s["reconciliation"]
    urls = {r["url"].rsplit("/", 1)[-1]: r for r in s["requests"]}
    assert urls["stream.bin"]["encoded"] and urls["stream.bin"]["worker"]
    if worker != "blob":
        assert urls["worker.js"]["encoded"] and urls["worker.js"]["completed_by_summary"]
