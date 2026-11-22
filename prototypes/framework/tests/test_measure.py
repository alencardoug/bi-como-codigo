"""The measures' accounting of §2.7, on synthetic journeys: the clock from
the protocol's pairs, bytes by cutoff with partial transfers labelled, the
cache evidence, and warm samples split into series by it — proved once on a
deliberately mismatched trace and once on an incomplete one."""

from __future__ import annotations

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
