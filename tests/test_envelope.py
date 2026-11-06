"""The envelope's Python reader, producer and package checks against the
oracles of docs/encryption_envelope.md §6. The JavaScript reader runs the same
vectors and cases in tests/js/envelope.test.mjs."""

from __future__ import annotations

import hashlib
import inspect
import json
import pathlib
import re
import struct

import pytest
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap

import envelope_fixtures as fx
from bi_como_codigo import envelope as e

ROOT = pathlib.Path(__file__).resolve().parent.parent
VECTORS = ROOT / "tests" / "vectors" / "envelope_v1"
SPEC = ROOT / "docs" / "encryption_envelope.md"
CASES = json.loads((VECTORS / "cases.json").read_text(encoding="utf-8"))["cases"]
VECTOR = json.loads((VECTORS / "vectors.json").read_text(encoding="utf-8"))

_KEYS: dict[tuple, e.ProfileKey] = {}


def key_for(manifest: e.Manifest, profile: str, typed: str) -> e.ProfileKey:
    p = manifest.profiles[profile]
    k = (manifest.package_id, profile, p.salt, p.iterations, typed)
    if k not in _KEYS:
        _KEYS[k] = e.login(manifest, profile, typed)
    return _KEYS[k]


def run(manifest_text: str, envelope: bytes, report: str, profile: str, typed: str):
    try:
        manifest = e.validate_manifest(manifest_text.encode("utf-8"))
        return e.open_report(manifest, envelope, report, key_for(manifest, profile, typed))
    except e.Refused as refusal:
        return refusal


# --- §6.1: the primitives against their standards ---------------------------------


@pytest.mark.parametrize(
    "password, salt, iterations, expected",
    [
        ("passwd", "salt", 1,
         "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc"
         "49ca9cccf179b645991664b39d77ef317c71b845b1e30bd509112041d3a19783"),
        ("Password", "NaCl", 80000,
         "4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56"
         "a1d425a1225833549adb841b51c9b3176a272bdebba1d078478f62b397f33c8d"),
    ],
)
def test_pbkdf2_matches_rfc_7914_section_11(password, salt, iterations, expected):
    out = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations, 64)
    assert out.hex() == expected


def test_aes_kw_matches_rfc_3394_section_4_6():
    from cryptography.hazmat.primitives.keywrap import aes_key_unwrap, aes_key_wrap

    kek = bytes(range(32))
    data = bytes.fromhex("00112233445566778899aabbccddeeff000102030405060708090a0b0c0d0e0f")
    wrapped = bytes.fromhex("28c9f404c4b810f4cbccb35cfb87f8263f5786e2d80ed326cbc7f0e71a99f43bfb988b9b7a02dd21")
    assert aes_key_wrap(kek, data) == wrapped
    assert aes_key_unwrap(kek, wrapped) == data


def test_aes_gcm_matches_test_case_16():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = bytes.fromhex("feffe9928665731c6d6a8f9467308308" * 2)
    iv = bytes.fromhex("cafebabefacedbaddecaf888")
    plain = bytes.fromhex(
        "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a72"
        "1c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39"
    )
    aad = bytes.fromhex("feedfacedeadbeeffeedfacedeadbeefabaddad2")
    expected = (
        "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa"
        "8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662"
        "76fc6ece0f4e1768cddf8853bb2d551b"
    )
    assert AESGCM(key).encrypt(iv, plain, aad).hex() == expected


# --- §6.2: the vectors -------------------------------------------------------------


def test_committed_fixtures_are_what_the_generator_builds():
    for name, content in fx.build().items():
        assert (VECTORS / name).read_text(encoding="utf-8") == content, f"{name} is stale: run tests/envelope_fixtures.py"


def test_each_vector_is_rebuilt_byte_for_byte_by_seal_report():
    for report_id, v in VECTOR["reports"].items():
        slots = [
            e.SlotInput(p, bytes.fromhex(VECTOR["salts"][p]), VECTOR["iterations"],
                        e.derive_kek(VECTOR["typed_by_profile"][p], bytes.fromhex(VECTOR["salts"][p]), VECTOR["iterations"]))
            for p in sorted(fx.ENTITLEMENTS) if report_id in fx.ENTITLEMENTS[p]
        ]
        payload = e.build_payload(bytes.fromhex(v["totals"]), bytes.fromhex(v["parquet"]))
        sealed = e.seal_report(bytes.fromhex(VECTOR["package_id"]), report_id, slots,
                               bytes.fromhex(v["dek"]), bytes.fromhex(v["iv"]), payload)
        assert sealed.hex() == v["envelope"]
        assert hashlib.sha256(sealed).hexdigest() == v["sha256"]


def test_the_vector_manifest_validates_and_holds_the_three_reports():
    manifest = e.validate_manifest((VECTORS / "manifest.json").read_bytes())
    assert sorted(manifest.reports) == ["P01", "P02", "P13"]
    assert manifest.entitled("P13") == {"diretoria", "logistica"}
    assert manifest.entitled("P01") == {"diretoria"}


# --- §6.3: the cases --------------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case):
    out = run(case["manifest"], bytes.fromhex(case["envelope"]), case["report"], case["profile"], case["typed"])
    if case["code"] is None:
        expected = VECTOR["reports"][case["report"]]
        assert out == (bytes.fromhex(expected["totals"]), bytes.fromhex(expected["parquet"]))
        return
    assert isinstance(out, e.Refused), f"{case['id']} opened"
    assert (out.code, out.predicate_id) == (case["code"], case["predicate"])


def _range_max_case() -> tuple[str, bytes]:
    """`header_ciphertext_range` above the bound: built here, not committed —
    the file holds exactly the 33,554,433 bytes it declares (§6.3)."""
    fields = fx.fields_of(bytes.fromhex(VECTOR["reports"]["P01"]["envelope"]))
    n = e.CIPHERTEXT_MAX + 1
    fields["body"] = bytes(n + e.TAG_LEN)
    data = fx.write(fields)
    manifest = json.loads((VECTORS / "manifest.json").read_text(encoding="utf-8"))
    manifest["reports"] = [fx.entry("P01", data) if r["id"] == "P01" else r for r in manifest["reports"]]
    return fx.text(manifest), data


def test_case_header_ciphertext_range_above_the_bound():
    manifest_text, data = _range_max_case()
    out = run(manifest_text, data, "P01", "diretoria", fx.TYPED["diretoria"])
    assert isinstance(out, e.Refused)
    assert (out.code, out.predicate_id) == ("header_malformed", "ciphertext_len_range")


def test_every_group_of_the_specification_has_cases():
    assert {c["group"] for c in CASES} == {"control", "M", "A", "H", "I", "S", "E", "U", "D", "P"}


# --- §6.5: the predicates are the specification's -----------------------------------


def spec_predicates() -> set[str]:
    """The `predicate_id`s of §6.5's table, the live ones of stage 2.2b included."""
    text = SPEC.read_text(encoding="utf-8")
    table = text.split("### 6.5")[1].split("\n### ")[0]
    ids: set[str] = set()
    for line in table.splitlines():
        cells = line.split("|")
        step = cells[1].strip() if len(cells) >= 4 else ""
        if not step or step in ("Step", "---"):
            continue
        ids |= set(re.findall(r"`([a-z0-9_]+)`", cells[2]))
    return ids


def module_predicates(source: str) -> set[str]:
    return set(re.findall(r'require\([^\n]*,\s*[A-Za-z_]+,\s*"([a-z0-9_]+)"\)', source))


def test_the_python_module_has_exactly_the_predicates_of_the_specification():
    source = pathlib.Path(e.__file__).read_text(encoding="utf-8")
    assert module_predicates(source) == spec_predicates()


def test_each_predicate_has_a_dedicated_case_or_test():
    covered = {c["predicate"] for c in CASES} | {"ciphertext_len_range", "dek_unique", "iv_unique", "matrix_closed"} | {
        "live_unchanged_identical", "live_dek_fresh", "live_iv_fresh", "live_salt_fresh", "live_opens"}  # the tests below
    assert spec_predicates() <= covered


# --- §6.4: the package checks ---------------------------------------------------------


def _package(deks: dict[str, bytes], ivs: dict[str, bytes], same_key: bool = False):
    salts = dict(fx.SALTS)
    typed = dict(fx.TYPED)
    if same_key:
        salts["logistica"] = salts["diretoria"]
        typed["logistica"] = typed["diretoria"]
    envelopes = {}
    for r in ("P01", "P02", "P13"):
        slots = [
            e.SlotInput(p, salts[p], e.ITERATIONS, fx.kek(p, salts[p], typed=typed[p]))
            for p in sorted(fx.ENTITLEMENTS) if r in fx.ENTITLEMENTS[p]
        ]
        envelopes[r] = e.seal_report(fx.PACKAGE_ID, r, slots, deks[r], ivs[r], e.build_payload(*fx.PAYLOADS[r]))
    manifest = fx.manifest_dict(envelopes)
    for p in manifest["profiles"]:
        p["salt"] = salts[p["id"]].hex()
    files = {fx.entry(r, d)["file"]: d for r, d in envelopes.items()}
    return fx.text(manifest).encode(), files, typed


def _fresh(label: str) -> tuple[dict[str, bytes], dict[str, bytes]]:
    return ({r: fx.fixed(f"{label} dek {r}", 32) for r in ("P01", "P02", "P13")},
            {r: fx.fixed(f"{label} iv {r}", 12) for r in ("P01", "P02", "P13")})


def test_reuse_control_is_accepted():
    deks, ivs = _fresh("control")
    manifest, files, typed = _package(deks, ivs)
    e.check_package(manifest, files, typed, expected=fx.PAYLOADS)


@pytest.mark.parametrize(
    "name, same_dek, same_iv, predicate",
    [("reuse_dek_only", True, False, "dek_unique"),
     ("reuse_iv_only", False, True, "iv_unique"),
     ("reuse_both", True, True, "dek_unique")],
)
def test_reuse_is_refused(name, same_dek, same_iv, predicate):
    deks, ivs = _fresh(name)
    if same_dek:
        deks["P02"] = deks["P01"]
    if same_iv:
        ivs["P02"] = ivs["P01"]
    manifest, files, typed = _package(deks, ivs)
    with pytest.raises(e.Refused) as refusal:
        e.check_package(manifest, files, typed)
    assert refusal.value.predicate_id == predicate


def test_matrix_same_key_is_refused():
    """Two profiles with the same password and salt share a KEK, so the
    unentitled one unwraps a slot that is not its own (§6.4)."""
    deks, ivs = _fresh("matrix")
    manifest, files, typed = _package(deks, ivs, same_key=True)
    with pytest.raises(e.Refused) as refusal:
        e.check_package(manifest, files, typed)
    assert (refusal.value.code, refusal.value.predicate_id) == ("unentitled_opens", "matrix_closed")


# --- §5.2: the producer --------------------------------------------------------------


def declaration():
    return [e.DeclaredProfile(p, fx.LABELS[p], fx.TYPED[p], fx.ENTITLEMENTS[p]) for p in sorted(fx.TYPED)]


def materials(manifest_raw: bytes, files: dict[str, bytes]) -> tuple[set[bytes], set[bytes]]:
    """The real DEKs, unwrapped with the public password of `diretoria`, which
    every report of the fixtures is entitled to, and the IVs of a package."""
    manifest = e.validate_manifest(manifest_raw)
    key = e.login(manifest, "diretoria", fx.TYPED["diretoria"])
    deks, ivs = set(), set()
    for data in files.values():
        header, _ = e.parse_header(data)
        slot = next(s for s in header.slots if s.profile_id == b"diretoria")
        deks.add(aes_key_unwrap(key.kek, slot.wrapped_key))
        ivs.add(header.iv)
    return deks, ivs


def test_encrypt_package_round_trips_and_draws_anew_each_run():
    first_manifest, first_files = e.encrypt_package(declaration(), fx.PAYLOADS)
    second_manifest, second_files = e.encrypt_package(declaration(), fx.PAYLOADS)
    one = json.loads(first_manifest)
    two = json.loads(second_manifest)
    assert one["package_id"] != two["package_id"]
    assert {p["salt"] for p in one["profiles"]}.isdisjoint({p["salt"] for p in two["profiles"]})
    assert set(first_files).isdisjoint(second_files)
    # The keys and IVs themselves, not what they change (ENV-4-04): a new header
    # alone would change the names and digests even with the same DEK and IV.
    first_deks, first_ivs = materials(first_manifest, first_files)
    second_deks, second_ivs = materials(second_manifest, second_files)
    assert len(first_deks) == len(first_ivs) == len(fx.PAYLOADS)
    assert first_deks.isdisjoint(second_deks)
    assert first_ivs.isdisjoint(second_ivs)
    e.check_package(first_manifest, first_files, fx.TYPED, expected=fx.PAYLOADS)


def test_encrypt_package_takes_no_random_source():
    assert list(inspect.signature(e.encrypt_package).parameters) == ["profiles", "payloads"]


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.__setitem__(0, e.DeclaredProfile("diretoria", "Diretoria", "senha com ç", d[0].reports)),
        lambda d: d.__setitem__(0, e.DeclaredProfile("Diretoria", "Diretoria", d[0].password, d[0].reports)),
        lambda d: d.__setitem__(1, e.DeclaredProfile("logistica", "Logística", d[1].password, ("P99",))),
        lambda d: d.__setitem__(0, e.DeclaredProfile("diretoria", "Diretoria", d[0].password, ("P01", "P01"))),
    ],
    ids=["password_not_ascii", "profile_id_uppercase", "unknown_report", "report_twice"],
)
def test_encrypt_package_refuses_a_bad_declaration(change):
    d = declaration()
    change(d)
    with pytest.raises(ValueError):
        e.encrypt_package(d, fx.PAYLOADS)


@pytest.mark.parametrize(
    "totals",
    [b"xx", b"[]", b"\xff\xff", b'{"x":1,"x":2}', b'{"x": NaN}'],
    ids=["not_json", "not_an_object", "not_utf8", "repeated_key", "nan"],
)
def test_encrypt_package_refuses_totals_that_are_not_one_json_object(totals):
    """§2.4, §5.2 step 1 (ENV-4-02): checked before anything is drawn."""
    payloads = dict(fx.PAYLOADS)
    payloads["P01"] = (totals, fx.PAYLOADS["P01"][1])
    with pytest.raises(ValueError, match="control totals"):
        e.encrypt_package(declaration(), payloads)


def test_encrypt_package_refuses_a_report_entitled_to_no_profile():
    payloads = dict(fx.PAYLOADS)
    payloads["P04"] = fx.PAYLOADS["P01"]
    with pytest.raises(ValueError):
        e.encrypt_package(declaration(), payloads)


def test_build_payload_is_the_layout_of_section_2_4():
    out = e.build_payload(b"{}", b"PAR1xxxxPAR1")
    assert out == b"BICP\x01" + struct.pack(">I", 2) + b"{}" + struct.pack(">I", 12) + b"PAR1xxxxPAR1"


# --- §6.4, against the package live (stage 2.2b) ------------------------------------------


def _sealed(package_id: bytes, salts: dict[str, bytes], deks: dict[str, bytes], ivs: dict[str, bytes], typed=None):
    """A package sealed with every input chosen: (manifest bytes, envelopes)."""
    typed = typed or fx.TYPED
    keks = {p: fx.kek(p, salts[p], typed=typed[p]) for p in fx.TYPED}
    files = {}
    for r in ("P01", "P02", "P13"):
        slots = [e.SlotInput(p, salts[p], e.ITERATIONS, keks[p]) for p in sorted(fx.ENTITLEMENTS) if r in fx.ENTITLEMENTS[p]]
        envelope = e.seal_report(package_id, r, slots, deks[r], ivs[r], e.build_payload(*fx.PAYLOADS[r]))
        files[e.file_name(r, envelope)] = envelope
    return e._manifest_bytes(package_id, declaration(), salts, files), files


def _live_inputs(tag: str) -> dict:
    return {
        "package_id": fx.fixed(f"{tag} package", 16),
        "salts": {p: fx.fixed(f"{tag} salt {p}", 16) for p in fx.TYPED},
        "deks": {r: fx.fixed(f"{tag} dek {r}", 32) for r in ("P01", "P02", "P13")},
        "ivs": {r: fx.fixed(f"{tag} iv {r}", 12) for r in ("P01", "P02", "P13")},
    }


@pytest.fixture(scope="module")
def live_package():
    return _sealed(**_live_inputs("live"))


def _against(live_package, candidate):
    e.check_against_live(*candidate, *live_package, dict(fx.TYPED))


def test_live_unchanged_is_accepted(live_package):
    _against(live_package, live_package)


def test_live_fresh_is_accepted(live_package):
    _against(live_package, _sealed(**_live_inputs("fresh")))


def test_live_same_id_changed_is_package_id_reused(live_package):
    """live_unchanged_identical: the live package_id, one envelope re-sealed."""
    inputs = _live_inputs("live")
    inputs["deks"]["P02"] = fx.fixed("another dek", 32)
    inputs["ivs"]["P02"] = fx.fixed("another iv", 12)
    with pytest.raises(e.Refused) as refusal:
        _against(live_package, _sealed(**inputs))
    assert (refusal.value.code, refusal.value.predicate_id) == (e.PACKAGE_ID_REUSED, "live_unchanged_identical")


@pytest.mark.parametrize(
    "field, code, predicate",
    [("deks", e.DEK_REUSED, "live_dek_fresh"), ("ivs", e.IV_REUSED, "live_iv_fresh"), ("salts", e.SALT_REUSED, "live_salt_fresh")],
    ids=["live_dek_reused", "live_iv_reused", "live_salt_reused"],
)
def test_a_new_package_reusing_live_material_is_refused(live_package, field, code, predicate):
    inputs = _live_inputs("new")
    key = "logistica" if field == "salts" else "P13"
    inputs[field][key] = _live_inputs("live")[field][key]
    with pytest.raises(e.Refused) as refusal:
        _against(live_package, _sealed(**inputs))
    assert (refusal.value.code, refusal.value.predicate_id) == (code, predicate)


def test_live_unopenable_is_live_unreadable():
    """live_opens: live sealed under other passwords than the declared ones."""
    other = {p: pw + "_old" for p, pw in fx.TYPED.items()}
    live = _sealed(**_live_inputs("old"), typed=other)
    with pytest.raises(e.Refused) as refusal:
        _against(live, _sealed(**_live_inputs("fresh")))
    assert (refusal.value.code, refusal.value.predicate_id) == (e.LIVE_UNREADABLE, "live_opens")
