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
    shutil.copyfile(f.REPO / "web" / "envelope.mjs", art / "envelope.mjs")
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
