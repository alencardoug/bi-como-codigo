"""The vectors and the negative cases of the envelope (§6.2, §6.3).

Run as a script, it writes `tests/vectors/envelope_v1/`; imported, it builds
the same bytes, and `test_envelope.py` checks the committed files are exactly
what it builds. Both readers — Python and JavaScript — consume the committed
files, so they are judged on the same bytes.

The headers of the negative cases are serialised here by a writer of its own,
field by field, and not by the module's `build_header`: a case must be able to
hold what the module would never write — slots out of order, a length byte
that lies —, and a defect in the module's writer must not hide in its tests.

Every value below is fixed and derived from a label, so that the vectors are
reproducible; none is random, and none protects anything. The two passwords
are the public ones of PLAN §3.2, registered in `docs/public_by_design.yml`.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Appended, not inserted: the counter-proof (§6.5) puts a mutant copy of the
# module first on the path, and this must not shadow it.
if str(ROOT / "src") not in sys.path:
    sys.path.append(str(ROOT / "src"))

from bi_como_codigo import envelope as e  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "envelope_v1"

TYPED = {"diretoria": "senha_complexa_123", "logistica": "complexa_senha_321"}
LABELS = {"diretoria": "Diretoria", "logistica": "Logística"}
ENTITLEMENTS = {"diretoria": ("P01", "P02", "P13"), "logistica": ("P13",)}


def fixed(label: str, n: int) -> bytes:
    """`n` bytes derived from a label: reproducible, distinct, not random."""
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(f"bi-como-codigo envelope v1 vector: {label} #{counter}".encode()).digest()
        counter += 1
    return out[:n]


PACKAGE_ID = fixed("package", 16)
SALTS = {p: fixed(f"salt {p}", 16) for p in TYPED}
#: A minimal stand-in for a Parquet file: its magic at both ends, 12 bytes in
#: all. The reader checks only the framing (§2.4); the Parquet itself is the
#: exporter's (stage 2.4).
def parquet(tag: bytes) -> bytes:
    return b"PAR1" + tag[:4] + b"PAR1"


#: P01 and P02 have payloads of the same length, so that one served as the
#: other differs in the SHA-256 and not in the size (case `foreign_envelope`).
PAYLOADS = {
    "P01": (b'{"rows": 1}', parquet(b"p01-")),
    "P02": (b'{"rows": 2}', parquet(b"p02-")),
    "P13": (b'{"rows": 13}', parquet(b"p13-")),
}

_KEKS: dict[tuple[str, bytes, int, str], bytes] = {}


def kek(profile: str, salt: bytes | None = None, iterations: int = e.ITERATIONS, typed: str | None = None) -> bytes:
    salt = SALTS[profile] if salt is None else salt
    typed = TYPED[profile] if typed is None else typed
    k = (profile, salt, iterations, typed)
    if k not in _KEKS:
        _KEKS[k] = e.derive_kek(typed, salt, iterations)
    return _KEKS[k]


def slots_for(report_id: str, salts: dict[str, bytes] | None = None) -> list[e.SlotInput]:
    salts = SALTS if salts is None else salts
    return [
        e.SlotInput(p, salts[p], e.ITERATIONS, kek(p, salts[p]))
        for p in sorted(ENTITLEMENTS)
        if report_id in ENTITLEMENTS[p]
    ]


def seal(report_id: str, package_id: bytes = PACKAGE_ID, salts=None, payload: bytes | None = None, label: str = "") -> bytes:
    payload = e.build_payload(*PAYLOADS[report_id]) if payload is None else payload
    return e.seal_report(
        package_id,
        report_id,
        slots_for(report_id, salts),
        fixed(f"dek {report_id}{label}", 32),
        fixed(f"iv {report_id}{label}", 12),
        payload,
    )


def manifest_dict(envelopes: dict[str, bytes]) -> dict:
    return {
        "manifest_version": 1,
        "envelope_format_version": 1,
        "package_id": PACKAGE_ID.hex(),
        "profiles": [
            {"id": p, "label": LABELS[p], "salt": SALTS[p].hex(), "iterations": e.ITERATIONS, "reports": list(ENTITLEMENTS[p])}
            for p in sorted(TYPED)
        ],
        "reports": [entry(r, envelopes[r]) for r in sorted(envelopes)],
    }


def entry(report_id: str, data: bytes) -> dict:
    sha = hashlib.sha256(data).hexdigest()
    return {"id": report_id, "file": f"{report_id}.{sha[:16]}.bice", "sha256": sha, "size": len(data)}


def text(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


# --- an independent header writer -----------------------------------------------


def fields_of(envelope: bytes) -> dict:
    """The fields of a valid envelope, read with the module's parser."""
    h, sealed = e.parse_header(envelope)
    return {
        "magic": e.MAGIC,
        "version": bytes([e.FORMAT_VERSION]),
        "algorithms": e.ALGORITHM_BYTES,
        "lengths": e.LENGTH_BYTES,
        "package_id": h.package_id,
        "report_id": h.report_id,
        "slots": [[s.profile_id, s.salt, s.iterations, s.wrapped_key] for s in h.slots],
        "iv": h.iv,
        "body": sealed,
    }


def write(f: dict, report_id_len: int | None = None, slot_count: int | None = None, ciphertext_len: int | None = None) -> bytes:
    """Field by field, in the order of §2.1; a length given overrides the true one."""
    out = bytearray(f["magic"] + f["version"] + f["algorithms"] + f["lengths"] + f["package_id"])
    out.append(len(f["report_id"]) if report_id_len is None else report_id_len)
    out += f["report_id"]
    out.append(len(f["slots"]) if slot_count is None else slot_count)
    for profile_id, salt, iterations, wrapped in f["slots"]:
        out.append(len(profile_id))
        out += profile_id + salt + struct.pack(">I", iterations) + wrapped
    out += f["iv"]
    out += struct.pack(">I", len(f["body"]) - e.TAG_LEN if ciphertext_len is None else ciphertext_len)
    return bytes(out + f["body"])


def flip(data: bytes, at: int, mask: int = 0x01) -> bytes:
    b = bytearray(data)
    b[at] ^= mask
    return bytes(b)


def header_len(envelope: bytes) -> int:
    return len(e.parse_header(envelope)[0].raw)


# --- the cases ------------------------------------------------------------------


def build() -> dict:
    vectors = {r: seal(r) for r in PAYLOADS}
    base = manifest_dict(vectors)
    cases: list[dict] = []

    def case(case_id, group, data, *, report="P01", profile="diretoria", typed=None, manifest=None,
             refresh=True, code=None, predicate=None, ci_only=False, manifest_text=None):
        m = json.loads(json.dumps(base if manifest is None else manifest))
        if refresh and manifest_text is None:
            m["reports"] = [entry(report, data) if r["id"] == report else r for r in m["reports"]]
        cases.append({
            "id": case_id,
            "group": group,
            "report": report,
            "profile": profile,
            "typed": TYPED[profile] if typed is None else typed,
            "manifest": manifest_text if manifest_text is not None else text(m),
            "envelope": data.hex(),
            "code": code,
            "predicate": predicate,
            "ci_only": ci_only,
        })

    p01, p02, p13 = vectors["P01"], vectors["P02"], vectors["P13"]

    # Controls: every entitled pair opens.
    for r, p in (("P01", "diretoria"), ("P02", "diretoria"), ("P13", "diretoria"), ("P13", "logistica")):
        case(f"opens_{r.lower()}_{p}", "control", vectors[r], report=r, profile=p)

    # M — the manifest (step 0).
    def mutated(fn):
        m = json.loads(json.dumps(base))
        fn(m)
        return m

    def rename_report(m, old, new):
        for r in m["reports"]:
            if r["id"] == old:
                r["id"] = new
        for p in m["profiles"]:
            p["reports"] = [new if x == old else x for x in p["reports"]]

    M = "manifest_invalid"
    manifest_cases = [
        ("manifest_keys", "extra_top_key", lambda m: m.update(extra=1)),
        ("manifest_keys", "missing_top_key", lambda m: m.pop("reports")),
        ("manifest_keys", "extra_profile_key", lambda m: m["profiles"][0].update(extra=1)),
        ("manifest_keys", "missing_report_key", lambda m: m["reports"][0].pop("size")),
        ("manifest_types", "package_id_number", lambda m: m.update(package_id=1)),
        ("manifest_types", "iterations_text", lambda m: m["profiles"][0].update(iterations="600000")),
        ("manifest_types", "iterations_boolean", lambda m: m["profiles"][0].update(iterations=True)),
        ("manifest_types", "size_zero", lambda m: m["reports"][0].update(size=0)),
        ("manifest_types", "reports_not_list", lambda m: m["profiles"][1].update(reports="P13")),
        ("manifest_versions", "manifest_version_2", lambda m: m.update(manifest_version=2)),
        ("manifest_versions", "format_version_2", lambda m: m.update(envelope_format_version=2)),
        ("manifest_hex", "package_id_upper", lambda m: m.update(package_id=m["package_id"].upper())),
        ("manifest_hex", "salt_short", lambda m: m["profiles"][0].update(salt=m["profiles"][0]["salt"][:-2])),
        ("manifest_hex", "sha256_short", lambda m: m["reports"][0].update(sha256=m["reports"][0]["sha256"][:-1])),
        ("manifest_identity_length", "profile_id_empty", lambda m: m["profiles"][0].update(id="")),
        ("manifest_identity_length", "report_id_17", lambda m: rename_report(m, "P13", "P" + "1" * 16)),
        ("manifest_identity_bytes", "report_id_final_lf", lambda m: rename_report(m, "P13", "P13\n")),
        ("manifest_identity_bytes", "report_id_final_space", lambda m: rename_report(m, "P13", "P13 ")),
        ("manifest_identity_bytes", "report_id_lowercase", lambda m: rename_report(m, "P13", "p13")),
        ("manifest_identity_bytes", "profile_id_uppercase", lambda m: m["profiles"][1].update(id="Logistica")),
        ("manifest_identity_bytes", "profile_id_final_lf", lambda m: m["profiles"][1].update(id="logistica\n")),
        ("manifest_identity_bytes", "profile_id_accented", lambda m: m["profiles"][1].update(id="logística")),
        ("manifest_iterations_bounds", "iterations_599999", lambda m: m["profiles"][1].update(iterations=599_999)),
        ("manifest_iterations_bounds", "iterations_2000001", lambda m: m["profiles"][1].update(iterations=2_000_001)),
        ("manifest_unique", "report_twice", lambda m: m["reports"].append(dict(m["reports"][-1]))),
        ("manifest_unique", "profile_lists_twice", lambda m: m["profiles"][1].update(reports=["P13", "P13"])),
        ("manifest_sorted", "profiles_reversed", lambda m: m.update(profiles=m["profiles"][::-1])),
        ("manifest_sorted", "reports_reversed", lambda m: m.update(reports=m["reports"][::-1])),
        ("manifest_sorted", "profile_reports_reversed", lambda m: m["profiles"][0].update(reports=m["profiles"][0]["reports"][::-1])),
        ("manifest_membership", "lists_unknown_report", lambda m: m["profiles"][1].update(reports=["P13", "P99"])),
        ("manifest_entitled", "report_of_no_profile", lambda m: m["reports"].append(entry("P99", b"x"))),
        ("manifest_file_form", "file_renamed", lambda m: m["reports"][0].update(file="P01.bice")),
    ]
    for predicate, name, fn in manifest_cases:
        case(f"manifest_shape__{name}", "M", p01, manifest=mutated(fn), refresh=False, code=M, predicate=predicate)
    duplicated = text(base).replace('"manifest_version": 1,', '"manifest_version": 1,\n  "manifest_version": 1,', 1)
    case("manifest_duplicate_key", "M", p01, manifest_text=duplicated, refresh=False, code=M,
         predicate="manifest_no_duplicate_keys", ci_only=True)

    # A — integrity (step 1): the manifest unchanged.
    A = "integrity_mismatch"
    case("size_only", "A", p01, manifest=mutated(lambda m: m["reports"][0].update(size=m["reports"][0]["size"] + 1)),
         refresh=False, code=A, predicate="size_equal")
    case("bit_flipped_unrefreshed", "A", flip(p01, len(p01) - 20), refresh=False, code=A, predicate="sha256_equal")
    case("foreign_envelope__other_report", "A", p02, refresh=False, code=A, predicate="sha256_equal")
    foreign = seal("P01", package_id=fixed("other package", 16), salts={p: fixed(f"other salt {p}", 16) for p in TYPED})
    case("foreign_envelope__other_package", "A", foreign, refresh=False, code=A, predicate="sha256_equal")

    # H — the header (step 2): the manifest entry refreshed.
    H = "header_malformed"
    f01 = fields_of(p01)
    f13 = fields_of(p13)
    hl = header_len(p01)
    boundaries = [1, 2, 4, 5, 8, 10, 13, 15, 20, 31, 32, 34, 35, 36, 37, 40, 46, 50, 62, 64, 66, 80, 106, 110, 118, 120]
    assert hl == 122, hl  # the boundaries above are P01's: one slot of `diretoria`
    for cut in boundaries:
        case(f"header_truncated__at_{cut}", "H", p01[:cut], code=H, predicate="bytes_available")
    case("header_fixed_byte__magic", "H", flip(p01, 0), code=H, predicate="magic")
    case("header_fixed_byte__version", "H", flip(p01, 4, 0x03), code=H, predicate="format_version")
    for at in range(5, 10):
        case(f"header_fixed_byte__algorithm_{at}", "H", flip(p01, at, 0x02), code=H, predicate="algorithm_bytes")
    for at in range(10, 15):
        case(f"header_fixed_byte__length_{at}", "H", flip(p01, at, 0x01), code=H, predicate="length_bytes")

    def with_fields(base_fields, **changes):
        f = {k: (list(map(list, v)) if k == "slots" else v) for k, v in base_fields.items()}
        f.update(changes)
        return f

    case("header_identity_bytes__report_len_0", "H", write(with_fields(f01, report_id=b"")), code=H, predicate="report_id_length")
    case("header_identity_bytes__report_len_17", "H", write(with_fields(f01, report_id=b"P" + b"1" * 16)), code=H, predicate="report_id_length")
    for name, rid in (("final_lf", b"P01\n"), ("lowercase", b"p01"), ("hyphen", b"P0-")):
        case(f"header_identity_bytes__report_{name}", "H", write(with_fields(f01, report_id=rid)), code=H, predicate="report_id_bytes")

    def slot_with(fields, index, **kw):
        f = with_fields(fields)
        s = f["slots"][index]
        for k, v in kw.items():
            s[{"profile_id": 0, "salt": 1, "iterations": 2, "wrapped": 3}[k]] = v
        return f

    case("header_identity_bytes__profile_len_0", "H", write(slot_with(f01, 0, profile_id=b"")), code=H, predicate="profile_id_length")
    case("header_identity_bytes__profile_len_33", "H", write(slot_with(f01, 0, profile_id=b"d" * 33)), code=H, predicate="profile_id_length")
    for name, pid in (("final_lf", b"diretoria\n"), ("uppercase", b"Diretoria")):
        case(f"header_identity_bytes__profile_{name}", "H", write(slot_with(f01, 0, profile_id=pid)), code=H, predicate="profile_id_bytes")
    case("header_slots_shape__count_0", "H", write(with_fields(f01, slots=[])), code=H, predicate="slot_count_range")
    case("header_slots_shape__count_9", "H", write(f01, slot_count=9), code=H, predicate="slot_count_range")
    case("header_slots_shape__reversed", "H", write(with_fields(f13, slots=f13["slots"][::-1])), report="P13", code=H, predicate="slots_ascending")
    case("header_slots_shape__repeated", "H", write(with_fields(f13, slots=[f13["slots"][0], f13["slots"][0]])), report="P13", code=H, predicate="slots_ascending")
    for it in (599_999, 2_000_001):
        case(f"header_iterations_bounds__{it}", "H", write(slot_with(f01, 0, iterations=it)), code=H, predicate="iterations_bounds")
    case("header_ciphertext_range__zero", "H", write(with_fields(f01, body=f01["body"][-e.TAG_LEN:])), code=H, predicate="ciphertext_len_range")
    case("header_ciphertext_len__plus_one", "H", write(f01, ciphertext_len=len(f01["body"]) - e.TAG_LEN + 1), code=H, predicate="ciphertext_available")
    case("header_ciphertext_len__cut_after_header", "H", p01[:hl], code=H, predicate="ciphertext_available")
    case("header_ciphertext_len__cut_in_ciphertext", "H", p01[: hl + 3], code=H, predicate="ciphertext_available")
    case("header_ciphertext_len__cut_in_tag", "H", p01[:-3], code=H, predicate="ciphertext_available")
    case("header_ciphertext_len__minus_one", "H", write(f01, ciphertext_len=len(f01["body"]) - e.TAG_LEN - 1), code=H, predicate="exact_end")
    case("header_trailing_byte", "H", p01 + b"\x00", code=H, predicate="exact_end")

    # I — identities (step 3).
    I = "identity_mismatch"
    other_id = fixed("expected package", 16).hex()
    case("package_expected_differs", "I", p01, manifest=mutated(lambda m: m.update(package_id=other_id)), code=I, predicate="package_id_equal")
    case("report_served_as_other", "I", p02, code=I, predicate="report_id_equal")

    # S — slots against the manifest (step 4).
    S = "slots_mismatch"
    case("slot_removed", "S", write(with_fields(f13, slots=f13["slots"][:1])), report="P13", code=S, predicate="slot_set_equal")
    extra = [b"logistica", SALTS["logistica"], e.ITERATIONS, fixed("extra wrapped", 40)]
    case("slot_added", "S", write(with_fields(f01, slots=f01["slots"] + [extra])), code=S, predicate="slot_set_equal")
    ff = fields_of(foreign)
    case("foreign_package_rewritten", "S", write(with_fields(ff, package_id=PACKAGE_ID)), code=S, predicate="slot_salt_equal")
    case("slot_salt_differs", "S", write(slot_with(f01, 0, salt=flip(f01["slots"][0][1], 0))), code=S, predicate="slot_salt_equal")
    case("slot_iterations_differs", "S", write(slot_with(f01, 0, iterations=600_001)), code=S, predicate="slot_iterations_equal")

    # E — entitlement (step 5).
    case("not_entitled", "E", p01, profile="logistica", code="not_entitled", predicate="slot_present")

    # U — unwrap (step 7): no predicate, the primitive refuses.
    U = "unwrap_failed"
    case("wrong_password__other_profiles", "U", p01, typed=TYPED["logistica"], code=U)
    case("wrong_password__logistica_with_diretoria", "U", p13, report="P13", profile="logistica", typed=TYPED["diretoria"], code=U)
    case("wrong_password__one_longer", "U", p13, report="P13", typed=TYPED["diretoria"] + "4", code=U)
    case("wrapped_key_bit", "U", write(slot_with(f01, 0, wrapped=flip(f01["slots"][0][3], 7))), code=U)
    salt_x = flip(SALTS["logistica"], 3)
    case("salt_both_sides", "U", write(slot_with(f13, 1, salt=salt_x)), report="P13", profile="logistica",
         manifest=mutated(lambda m: m["profiles"][1].update(salt=salt_x.hex())), code=U)
    case("iterations_both_sides", "U", write(slot_with(f13, 0, iterations=600_001)), report="P13",
         manifest=mutated(lambda m: m["profiles"][0].update(iterations=600_001)), code=U)

    # D — decryption (step 8): the last mutation is the one under test.
    D = "decrypt_failed"
    case("iv_bit", "D", write(with_fields(f01, iv=flip(f01["iv"], 0))), code=D)
    case("tag_bit", "D", flip(p01, len(p01) - 1), code=D)
    case("ciphertext_bit", "D", flip(p01, hl), code=D)
    case("report_id_rewritten", "D", write(with_fields(fields_of(p02), report_id=b"P01")), code=D)
    case("package_id_rewritten", "D", write(with_fields(f01, package_id=fixed("rewritten package", 16))),
         manifest=mutated(lambda m: m.update(package_id=fixed("rewritten package", 16).hex())), code=D)
    case("other_slot_bit", "D", write(slot_with(f13, 0, wrapped=flip(f13["slots"][0][3], 9))), report="P13", profile="logistica", code=D)

    # P — the payload (step 9), sealed validly around a bad one.
    P = "payload_malformed"
    t, q = PAYLOADS["P01"]
    good = e.build_payload(t, q)
    bad_payloads = [
        ("short", good[:7], "payload_exact"),
        ("magic", b"BICX" + good[4:], "payload_magic"),
        ("version", good[:4] + b"\x02" + good[5:], "payload_version"),
        ("totals_len_0", good[:5] + struct.pack(">I", 0) + good[9:], "totals_len_range"),
        ("totals_len_1", good[:5] + struct.pack(">I", 1) + good[9:], "totals_len_range"),
        ("totals_len_65537", good[:5] + struct.pack(">I", 65_537) + good[9:], "totals_len_range"),
        ("totals_past_end", good[:5] + struct.pack(">I", len(good)) + good[9:], "payload_exact"),
        ("parquet_len_11", e.PAYLOAD_MAGIC + b"\x01" + struct.pack(">I", len(t)) + t + struct.pack(">I", 11) + q[:11], "parquet_len_minimum"),
        ("trailing_byte", good + b"\x00", "payload_exact"),
        ("parquet_head", e.build_payload(t, b"PAR0" + q[4:]), "parquet_magic"),
        ("parquet_tail", e.build_payload(t, q[:-4] + b"PAR0"), "parquet_magic"),
    ]
    for name, payload, predicate in bad_payloads:
        case(f"payload_shape__{name}", "P", seal("P01", payload=payload, label=f" payload {name}"), code=P, predicate=predicate)

    vector_file = {
        "about": "Format version 1 of docs/encryption_envelope.md, §6.2. Fixed inputs derived from labels; nothing here is random or protects anything.",
        "typed_by_profile": TYPED,
        "package_id": PACKAGE_ID.hex(),
        "salts": {p: s.hex() for p, s in SALTS.items()},
        "iterations": e.ITERATIONS,
        "reports": {
            r: {
                "dek": fixed(f"dek {r}", 32).hex(),
                "iv": fixed(f"iv {r}", 12).hex(),
                "totals": PAYLOADS[r][0].hex(),
                "parquet": PAYLOADS[r][1].hex(),
                "envelope": vectors[r].hex(),
                "sha256": hashlib.sha256(vectors[r]).hexdigest(),
            }
            for r in sorted(vectors)
        },
    }
    return {
        "manifest.json": text(base),
        "vectors.json": json.dumps(vector_file, indent=2) + "\n",
        "cases.json": json.dumps({"about": "The negative cases and controls of §6.3, consumed by both readers.", "cases": cases}, ensure_ascii=False, indent=1) + "\n",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, content in build().items():
        (OUT / name).write_text(content, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT) / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
