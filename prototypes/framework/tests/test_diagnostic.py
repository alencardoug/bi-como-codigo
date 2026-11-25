"""The browser diagnostic's own proofs (§2.5.3, §2.5.5), on the control page
of `controls/page/`: each leak is reported where it was seen, a clean journey
reports none, and a changed pinned body is inconclusive. They prove the
diagnostic can see what it reports, not that it sees everything; none of them
is a verdict (N96)."""

from __future__ import annotations

import hashlib
import json
import shutil
import struct

import pytest

import diagnose as d
import fixture as f
import inspect_output as io_
import leveldb

pytestmark = pytest.mark.skipif(not (shutil.which("google-chrome") and shutil.which("node")), reason="Chrome or Node is not installed")

PINNED_URL = "https://cdn.jsdelivr.net/npm/bice-control@1.0.0/pinned.js"
PINNED = b"/* pinned */ globalThis.biceControlPinned = 1;\n"


@pytest.fixture(scope="module")
def control(tmp_path_factory):
    fx, _ = f.generate(20261120)
    manifest, files = f.seal(*f.payload(fx))
    art = tmp_path_factory.mktemp("control") / "artifact"
    shutil.copytree(f.HERE / "controls" / "page", art)
    shutil.copyfile(f.REPO / "site" / "app" / "envelope.mjs", art / "envelope.mjs")
    (art / "package").mkdir()
    (art / "package" / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (art / "package" / name).write_bytes(data)
    validated = {"manifest.json": hashlib.sha256(manifest).hexdigest()} | {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}
    return art, io_.Needles.from_fixture(fx), validated


def _journey(control, tmp_path, leak, body=PINNED):
    art, needles, validated = control
    return d.run(art, needles, out=tmp_path / "out", query=f"?leak={leak}", cdn={PINNED_URL: hashlib.sha256(PINNED).hexdigest()},
                 fulfill={PINNED_URL: body}, validated=validated, timeout=300)


def test_a_clean_journey_reports_nothing_and_decrypts_only_when_expected(control, tmp_path):
    r = _journey(control, tmp_path, "none")
    assert all(r.journey[k] for k in ("loginBox", "wrongShown", "summary", "newLogin"))
    assert r.leads() == []
    assert [(c["method"], c["outcome"], c["attempt"]) for c in r.decrypt] == [
        ("deriveKey", "ok", "wrong"), ("unwrapKey", "fail", "wrong"),
        ("deriveKey", "ok", "right"), ("unwrapKey", "ok", "right"), ("decrypt", "ok", "right")]
    assert {x["reason"] for x in r.fetches["recorded"]} >= {"pinned third-party body", "validated envelope"}


def test_a_decryption_at_startup_is_premature_before_any_submission_and_on_the_new_page(control, tmp_path):
    """The page opens the package with the public password on load: derivation,
    unwrap and decrypt, all before any submission, and again on the new page."""
    calls = [(c["method"], c["when"]) for c in _journey(control, tmp_path, "startup").decrypt if c["code"] == d.PREMATURE_DECRYPT]
    for when in ("before any submission", "on the new page before a new submission"):
        assert {m for m, w in calls if w == when} == {"deriveKey", "unwrapKey", "decrypt"}


def test_a_decryption_in_the_wrong_attempt_is_unexpected(control, tmp_path):
    codes = [c["code"] for c in _journey(control, tmp_path, "wrong").decrypt if c.get("attempt") == "wrong"]
    assert d.UNEXPECTED_DECRYPT in codes


def test_a_value_in_local_storage_is_seen_written_readable_and_on_disk_and_a_cookie_unobserved_on_disk(control, tmp_path):
    r = _journey(control, tmp_path, "local")
    assert io_.INSPECT_TEXT in {x["code"] for x in r.written["findings"]}
    assert {x["file"] for x in r.readable["findings"]} >= {"localStorage:p01", "cookie:p01"}
    assert any("Local Storage/leveldb" in x["file"] for x in r.on_disk["findings"])
    assert {"file": "Cookies", "field": "cookies.encrypted_value", "why": "kept encrypted by Chromium"} in r.on_disk["unobserved"]


def test_a_result_written_to_indexeddb_and_deleted_is_seen_by_the_write(control, tmp_path):
    r = _journey(control, tmp_path, "idb")
    assert any(x["file"].endswith("indexedDB.put") for x in r.written["findings"])
    assert not r.readable["findings"]


def test_a_selection_in_the_history_state_is_seen(control, tmp_path):
    r = _journey(control, tmp_path, "history")
    assert any("history.replaceState" in x["file"] for x in r.written["findings"])


def test_a_logout_that_keeps_the_worker_is_reported(control, tmp_path):
    assert [s["what"] for s in _journey(control, tmp_path, "worker").survives] == ["workers alive after logout"]


def test_a_changed_pinned_body_is_inconclusive(control, tmp_path):
    r = _journey(control, tmp_path, "none", body=PINNED + b"//")
    assert {x["reason"] for x in r.fetches["inconclusive"]} == {"a body at a declared URL with another digest"}


def test_snappy_literals_and_copies():
    # "abcabcabcabc": length 12, a literal "abc", then a copy of 9 bytes at offset 3.
    stream = bytes([12, (3 - 1) << 2]) + b"abc" + bytes([((9 - 1) << 2) | 2, 3, 0])
    assert leveldb.snappy(stream) == b"abcabcabcabc"
    with pytest.raises(leveldb.Unreadable):
        leveldb.snappy(bytes([4, ((4 - 1) << 2) | 2, 9, 0]))


# --- boundaries, read-backs and committed writes (PROTO-1-11, -12) ----------------------


def test_a_decryption_in_the_old_documents_logout_handler_is_the_sessions(control, tmp_path):
    r = _journey(control, tmp_path, "logoutcrypto")
    assert [(c["method"], c["when"]) for c in r.decrypt if c["code"] == d.PREMATURE_DECRYPT] == [
        ("decrypt", "after logout in the session's own document")]


def test_the_hooks_record_what_the_browser_stored_without_running_the_pages_getters(control, tmp_path):
    r = _journey(control, tmp_path, "getter")
    raw = json.loads((tmp_path / "out" / "raw.json").read_text())
    assert raw["end"]["titleBeforeLogout"] == "reads=1"
    assert [e["value"] for e in raw["events"] if e["kind"] == "store" and e["store"] == "history"] == [{"text": '{"v":1}'}]


def test_a_label_inside_a_stored_parquet_is_found_written_committed_and_readable(control, tmp_path):
    r = _journey(control, tmp_path, "label")
    raw = json.loads((tmp_path / "out" / "raw.json").read_text())
    stored = next(e["value"]["text"] for e in raw["events"] if e["kind"] == "store" and e["store"] == "localStorage")
    found = io_.inspect_items([io_.Item("stored", stored.encode(), role=io_.COLLECTED)], control[1])
    labels = {x.value for x in found.findings if x.code == io_.INSPECT_PARQUET}
    assert labels & set(f.CHANNELS), "the Parquet's text cells, not only its numbers"  # PROTO-2-11
    assert io_.INSPECT_PARQUET in {x["code"] for x in r.written["findings"]}
    assert io_.INSPECT_PARQUET in {x["code"] for x in r.written["committed"]["findings"]}
    assert io_.INSPECT_PARQUET in {x["code"] for x in r.readable["findings"]}


def test_a_transient_property_write_no_hook_sees_is_committed(control, tmp_path):
    r = _journey(control, tmp_path, "transient")
    assert not r.written["findings"]
    assert [x["code"] for x in r.written["committed"]["findings"]] == [io_.INSPECT_TEXT]
    assert {"store": "localStorage", "op": "domStorageItemRemoved", "name": "p01"} in r.written["content_changes"]


def test_a_cachestorage_write_is_seen_by_the_hook_the_protocol_and_the_end(control, tmp_path):
    r = _journey(control, tmp_path, "cache")
    assert any(x["file"].endswith("CacheStorage.put") for x in r.written["findings"])
    assert {"store": "CacheStorage", "op": "cacheStorageContentUpdated", "name": "bice-control"} in r.written["content_changes"]
    assert r.readable["findings"]


def test_a_truncated_leveldb_log_is_unreadable():
    record = struct.pack("<IHB", 0, 40, 1) + b"x" * 10
    with pytest.raises(leveldb.Unreadable):
        list(leveldb.read_log(record))


def test_a_realm_whose_hooks_never_answered_is_unobserved():
    raw = {"events": [{"kind": "installed", "target": "p1"}], "targets": {"p1": {"type": "page", "url": "http://x/"},
                                                                         "w1": {"type": "worker", "url": "blob:http://x/1"}}}
    assert d.unacknowledged(raw) == [{"what": "hooks", "target": "worker", "url": "blob:http://x/1", "why": "no acknowledgement from this realm"}]


# --- round 2 (PROTO-2-09, -10) --------------------------------------------------------


def test_two_writes_to_one_store_are_not_read_back_as_one(control, tmp_path):
    r = _journey(control, tmp_path, "idbtwice")
    assert any("later write" in x["why"] for x in r.written["unobserved"])


def test_a_map_and_a_blob_surviving_in_indexeddb_are_read_at_the_end(control, tmp_path):
    r = _journey(control, tmp_path, "mapblob")
    files = {x["file"] for x in r.readable["findings"]}
    assert any(f.endswith("> blob") for f in files) and any(f.startswith("indexedDB:") and not f.endswith("> blob") for f in files)


def test_two_blobs_of_one_record_are_two_bodies(control, tmp_path):
    """PROTO-3-11: the first Blob, holding the fixture's net total, is read
    even with a second Blob in the same record."""
    r = _journey(control, tmp_path, "twoblobs")
    assert any(x["file"].endswith("> blob") for x in r.readable["findings"])


def test_a_cache_write_deleted_before_the_end_is_read_when_it_changes(control, tmp_path):
    r = _journey(control, tmp_path, "transientcache")
    assert any("CacheStorage" in x["file"] for x in r.written["committed"]["findings"])
    assert not r.readable["findings"]


def test_a_missing_page_boundary_is_taken_from_the_driver_and_reported():
    events = [{"kind": "mark", "mark": "submit", "t": 1, "doc": "d1", "targetType": "page"},
              {"kind": "mark", "mark": "submit", "t": 2, "doc": "d1", "targetType": "page"}]
    marks, gaps = d.journey_marks(events, [{"mark": "logout", "t": 3}])
    assert [m["mark"] for m in marks] == ["submit", "submit", "logout"]
    assert gaps and "logout" in gaps[0]["what"]


def test_a_log_ending_inside_a_fragmented_record_is_unreadable():
    record = struct.pack("<IHB", 0, 4, 2) + b"abcd"
    with pytest.raises(leveldb.Unreadable, match="fragmented"):
        list(leveldb.read_log(record))


def _simple_entry(url: str, rest: bytes) -> bytes:
    """A Chrome simple-cache entry: its header, the key, then the rest."""
    key = f"1/0/_dk_http://127.0.0.1 http://127.0.0.1 {url}".encode()
    return struct.pack("<QIIII", d._SIMPLE_MAGIC, 5, len(key), 0, 0) + key + rest


def test_only_attributable_parts_of_a_cache_entry_are_taken_out():
    body = b"export const v = 1;\n" * 8
    entry = _simple_entry("http://127.0.0.1:5000/app.js", body + b'\x00ETag: "abc123"')
    assert d.cache_key_url(entry) == "http://127.0.0.1:5000/app.js"
    data, taken = d._cache_entry(entry, {"http://127.0.0.1:5000/app.js": body}, {'"abc123"'})
    assert body not in data and b"abc123" not in data and len(taken) == 2
    other = _simple_entry("http://127.0.0.1:5000/other.js", body)
    data, taken = d._cache_entry(other, {"http://127.0.0.1:5000/app.js": body}, set())
    assert body in data and not taken


def test_a_url_named_inside_an_entry_is_not_its_key_and_a_tag_in_data_stays():
    """PROTO-3-09: a `Link` naming another file does not key the entry, and a
    value equal to an issued validator outside an `ETag` field is inspected."""
    app = b'{"total": 63191}'
    entry = _simple_entry("http://127.0.0.1:5000/generated.json", app + b"\x00Link: <http://127.0.0.1:5000/app.json>; rel=preload")
    data, taken = d._cache_entry(entry, {"http://127.0.0.1:5000/app.json": app}, set())
    assert app in data and not taken
    tag = '"' + "6" * 64 + '"'
    entry = _simple_entry("http://127.0.0.1:5000/data.json", b'{"v": ' + tag.encode() + b"}" + b"\x00ETag: " + tag.encode())
    data, taken = d._cache_entry(entry, {}, {tag})
    assert data.count(tag.encode()) == 1 and data.endswith(b"ETag: ")
    assert d.cache_key_url(b"not an entry at all, just bytes") is None


@pytest.mark.parametrize("missing", [0, 1])
def test_a_missing_submit_is_the_driver_action_no_page_mark_stands_for(missing):
    """PROTO-3-10: driver submits at 10 and 20, logout at 30; the page marks
    every boundary but one submit. The missing one is taken where the driver
    made it, and a derivation inside the wrong attempt stays expected."""
    page = {0: 11, 1: 21}
    events = [{"kind": "mark", "mark": "submit", "t": t, "doc": "d1", "targetType": "page"} for n, t in page.items() if n != missing]
    events.append({"kind": "mark", "mark": "logout", "t": 31, "doc": "d1", "targetType": "page"})
    events += [{"kind": "crypto", "phase": "start", "target": "p", "doc": "d1", "id": 1, "method": "deriveKey", "realm": "page",
                "targetType": "page", "t": 12 if missing == 1 else 10.5},
               {"kind": "crypto", "phase": "ok", "target": "p", "doc": "d1", "id": 1}]
    driver = [{"mark": "submit", "t": 10}, {"mark": "submit", "t": 20}, {"mark": "logout", "t": 30}]
    marks, gaps = d.journey_marks(events, driver)
    submits = [m for m in marks if m["mark"] == "submit"]
    assert [m["t"] for m in submits] == sorted([10 if missing == 0 else 11, 20 if missing == 1 else 21])
    assert gaps and "submit" in gaps[0]["what"]
    calls = d.decrypt_calls(events, marks)
    assert [c["code"] for c in calls] == ["expected"] and calls[0]["attempt"] == "wrong"
    assert "uncertain" in calls[0]


def test_a_failed_baseline_keeps_the_journey_and_says_so(control, tmp_path, monkeypatch):
    """PROTO-3-09: the pristine profile not made is a gap, not a lost journey."""
    def broken(chrome=None):
        raise RuntimeError("injected")

    monkeypatch.setattr(d, "baseline", broken)
    r = _journey(control, tmp_path, "none")
    assert r.journey.get("newLogin") and r.decrypt
    assert any(x.get("what") == "pristine profile" for x in r.unobserved)


def test_the_profile_files_behind_on_disk_findings_are_kept(control, tmp_path):
    """PROTO-3-09: a lead on disk can be attributed after the profile is gone."""
    r = _journey(control, tmp_path, "local")
    assert r.on_disk["findings"]
    kept = [p for p in (tmp_path / "out" / "on_disk_sources").rglob("*") if p.is_file()]
    assert kept
