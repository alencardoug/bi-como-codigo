"""The encryption envelope, format version 1.

The specification is `docs/encryption_envelope.md`; this module implements it
and nothing else. Section numbers below (§n) are that document's.

Three things live here, in the order the document gives them:

* the reader — `validate_manifest`, `login` and `open_report` (§5.1);
* the producer — `seal_report`, pure, with every input explicit, and
  `encrypt_package`, which draws everything from the operating system's
  generator and takes no random source (§5.2);
* the package checks the producer and the CI gate run (§6.4).

Every condition that refuses is one `require(condition, code, predicate_id)`
call on a line of its own, with no side effect in the condition: the
counter-proof of §6.5 copies this file and takes one predicate as true, and
that only works if reading and checking stay separate.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import struct
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.keywrap import InvalidUnwrap, aes_key_unwrap, aes_key_wrap

# --- §2.1: the constants of format version 1 --------------------------------

MAGIC = b"BICE"
FORMAT_VERSION = 1
#: Offsets 5-9: password encoding, KDF, its PRF, the wrap and the cipher.
ALGORITHM_BYTES = bytes([1, 1, 1, 1, 1])
#: Offsets 10-14: key, salt, IV, tag and wrapped-key lengths.
LENGTH_BYTES = bytes([32, 16, 12, 16, 40])
KEY_LEN, SALT_LEN, IV_LEN, TAG_LEN, WRAPPED_LEN = LENGTH_BYTES
PACKAGE_ID_LEN = 16
REPORT_ID_MAX = 16
PROFILE_ID_MAX = 32
SLOT_COUNT_MAX = 8
ITERATIONS_MIN = 600_000
ITERATIONS_MAX = 2_000_000
#: What the producer of version 1 writes (N67).
ITERATIONS = ITERATIONS_MIN
CIPHERTEXT_MAX = 32 * 1024 * 1024

# --- §2.4: the payload ---------------------------------------------------------

PAYLOAD_MAGIC = b"BICP"
PAYLOAD_VERSION = 1
TOTALS_MIN, TOTALS_MAX = 2, 65_536
PARQUET_MIN = 12
PARQUET_MAGIC = b"PAR1"

# --- §5.1: the refusal codes -----------------------------------------------------

MANIFEST_INVALID = "manifest_invalid"
INTEGRITY_MISMATCH = "integrity_mismatch"
HEADER_MALFORMED = "header_malformed"
IDENTITY_MISMATCH = "identity_mismatch"
SLOTS_MISMATCH = "slots_mismatch"
NOT_ENTITLED = "not_entitled"
UNWRAP_FAILED = "unwrap_failed"
DECRYPT_FAILED = "decrypt_failed"
PAYLOAD_MALFORMED = "payload_malformed"
# §6.4: the package checks.
DEK_REUSED = "dek_reused"
IV_REUSED = "iv_reused"
UNENTITLED_OPENS = "unentitled_opens"
# §6.4, against the package live (stage 2.2b).
PACKAGE_ID_REUSED = "package_id_reused"
SALT_REUSED = "salt_reused"
LIVE_UNREADABLE = "live_unreadable"


class Refused(Exception):
    """A refusal of the reader or of the package checks: a code, and the
    predicate that failed — `None` for steps 7 and 8, the primitives' own."""

    def __init__(self, code: str, predicate_id: str | None) -> None:
        super().__init__(f"{code} ({predicate_id})" if predicate_id else code)
        self.code = code
        self.predicate_id = predicate_id


def require(condition: bool, code: str, predicate_id: str) -> None:
    if not condition:
        raise Refused(code, predicate_id)


# --- §3: identities, byte by byte, with no regular expression --------------------

_UPPER = range(0x41, 0x5B)
_LOWER = range(0x61, 0x7B)
_DIGIT = range(0x30, 0x3A)
_UNDERSCORE = 0x5F


def _identity_bytes_ok(value: bytes, lead: range) -> bool:
    """Every byte in range: the first in `lead`, the others in `lead`, the
    digits or the underscore. Length is checked apart, by its own predicate."""
    if not value or value[0] not in lead:
        return False
    return all(b in lead or b in _DIGIT or b == _UNDERSCORE for b in value[1:])


def report_id_ok(value: bytes) -> bool:
    return _identity_bytes_ok(value, _UPPER)


def profile_id_ok(value: bytes) -> bool:
    return _identity_bytes_ok(value, _LOWER)


def _ascii(text: str) -> bytes | None:
    """The bytes of an identity given as text, or None when any character is
    outside ASCII — such an identity can match no range anyway."""
    try:
        return text.encode("ascii")
    except UnicodeEncodeError:
        return None


# --- §4: the manifest ---------------------------------------------------------------

_TOP_KEYS = {"manifest_version", "envelope_format_version", "package_id", "profiles", "reports"}
_PROFILE_KEYS = {"id", "label", "salt", "iterations", "reports"}
_REPORT_KEYS = {"id", "file", "sha256", "size"}
_HEX = set(b"0123456789abcdef")


def _hex_ok(value: str, length: int) -> bool:
    raw = _ascii(value)
    return raw is not None and len(raw) == length and all(b in _HEX for b in raw)


#: The largest integer both runtimes hold exactly: JavaScript's numbers are
#: doubles, and `JSON.parse` keeps no trace of how a number was spelt.
SAFE_INTEGER_MAX = 2**53 - 1


def _is_int(value: object) -> bool:
    """An integer of the manifest (§4, ENV-4-01): a number whose value is
    integral and within ±(2^53 - 1), however it was spelt — `1`, `1.0` and
    `1e0` are one value, as they are to `JSON.parse`. Booleans are not numbers."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return abs(value) <= SAFE_INTEGER_MAX
    if isinstance(value, float):
        return value.is_integer() and abs(value) <= SAFE_INTEGER_MAX
    return False


def _strict_json(raw: bytes) -> tuple[bool, object]:
    """UTF-8, one JSON value, no repeated key and no `NaN` or `Infinity` —
    what CI accepts (§2.4, §4). Returns (parsed, value); a repeated key is
    refused by its own predicate, through the hook."""

    def no_constants(name: str) -> object:
        raise ValueError(name)

    try:
        return True, json.loads(raw.decode("utf-8"), object_pairs_hook=_refuse_duplicate_keys, parse_constant=no_constants)
    except (UnicodeDecodeError, ValueError):
        return False, None


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    salt: bytes
    iterations: int
    reports: tuple[str, ...]


@dataclass(frozen=True)
class ReportEntry:
    id: str
    file: str
    sha256: str
    size: int


@dataclass(frozen=True)
class Manifest:
    package_id: bytes
    profiles: dict[str, Profile]
    reports: dict[str, ReportEntry]

    def entitled(self, report_id: str) -> set[str]:
        return {p.id for p in self.profiles.values() if report_id in p.reports}


def _refuse_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    keys = [k for k, _ in pairs]
    require(len(keys) == len(set(keys)), MANIFEST_INVALID, "manifest_no_duplicate_keys")
    return dict(pairs)


def _ids_ok(ids: list[str], lead: range, maximum: int) -> tuple[bool, bool]:
    """(lengths in bounds, bytes in range) for a list of identities."""
    raws = [_ascii(i) for i in ids]
    lengths = all(r is None or 1 <= len(r) <= maximum for r in raws) and all(len(i) >= 1 for i in ids)
    content = all(r is not None and _identity_bytes_ok(r, lead) for r in raws)
    return lengths, content


def validate_manifest(raw: bytes) -> Manifest:
    """Step 0, strictly — the CI reader. The browser's is `web/envelope.mjs`,
    which cannot see a duplicate key (§4)."""
    parsed, data = _strict_json(raw)
    require(parsed, MANIFEST_INVALID, "manifest_types")
    return _validate_manifest_object(data)


def _validate_manifest_object(data: object) -> Manifest:
    require(isinstance(data, dict), MANIFEST_INVALID, "manifest_types")
    require(set(data) == _TOP_KEYS, MANIFEST_INVALID, "manifest_keys")
    profiles = data["profiles"]
    reports = data["reports"]
    require(isinstance(profiles, list) and isinstance(reports, list), MANIFEST_INVALID, "manifest_types")
    require(all(isinstance(p, dict) for p in profiles + reports), MANIFEST_INVALID, "manifest_types")
    require(all(set(p) == _PROFILE_KEYS for p in profiles), MANIFEST_INVALID, "manifest_keys")
    require(all(set(r) == _REPORT_KEYS for r in reports), MANIFEST_INVALID, "manifest_keys")
    types_ok = (
        _is_int(data["manifest_version"])
        and _is_int(data["envelope_format_version"])
        and isinstance(data["package_id"], str)
        and all(
            isinstance(p["id"], str)
            and isinstance(p["label"], str)
            and isinstance(p["salt"], str)
            and _is_int(p["iterations"])
            and isinstance(p["reports"], list)
            and all(isinstance(r, str) for r in p["reports"])
            for p in profiles
        )
        and all(
            isinstance(r["id"], str)
            and isinstance(r["file"], str)
            and isinstance(r["sha256"], str)
            and _is_int(r["size"])
            and r["size"] >= 1
            for r in reports
        )
    )
    require(types_ok, MANIFEST_INVALID, "manifest_types")
    versions_ok = data["manifest_version"] == 1 and data["envelope_format_version"] == FORMAT_VERSION
    require(versions_ok, MANIFEST_INVALID, "manifest_versions")
    hex_ok = (
        _hex_ok(data["package_id"], 2 * PACKAGE_ID_LEN)
        and all(_hex_ok(p["salt"], 2 * SALT_LEN) for p in profiles)
        and all(_hex_ok(r["sha256"], 64) for r in reports)
    )
    require(hex_ok, MANIFEST_INVALID, "manifest_hex")
    profile_ids = [p["id"] for p in profiles]
    report_ids = [r["id"] for r in reports]
    listed = [r for p in profiles for r in p["reports"]]
    p_len, p_bytes = _ids_ok(profile_ids, _LOWER, PROFILE_ID_MAX)
    r_len, r_bytes = _ids_ok(report_ids + listed, _UPPER, REPORT_ID_MAX)
    require(p_len and r_len, MANIFEST_INVALID, "manifest_identity_length")
    require(p_bytes and r_bytes, MANIFEST_INVALID, "manifest_identity_bytes")
    iterations_ok = all(ITERATIONS_MIN <= p["iterations"] <= ITERATIONS_MAX for p in profiles)
    require(iterations_ok, MANIFEST_INVALID, "manifest_iterations_bounds")
    unique_ok = (
        len(set(profile_ids)) == len(profile_ids)
        and len(set(report_ids)) == len(report_ids)
        and all(len(set(p["reports"])) == len(p["reports"]) for p in profiles)
    )
    require(unique_ok, MANIFEST_INVALID, "manifest_unique")
    sorted_ok = (
        profile_ids == sorted(profile_ids, key=_ascii)
        and report_ids == sorted(report_ids, key=_ascii)
        and all(p["reports"] == sorted(p["reports"], key=_ascii) for p in profiles)
    )
    require(sorted_ok, MANIFEST_INVALID, "manifest_sorted")
    require(set(listed) <= set(report_ids), MANIFEST_INVALID, "manifest_membership")
    require(set(report_ids) <= set(listed), MANIFEST_INVALID, "manifest_entitled")
    files_ok = all(r["file"] == f"{r['id']}.{r['sha256'][:16]}.bice" for r in reports)
    require(files_ok, MANIFEST_INVALID, "manifest_file_form")
    return Manifest(
        package_id=bytes.fromhex(data["package_id"]),
        profiles={
            p["id"]: Profile(p["id"], p["label"], bytes.fromhex(p["salt"]), int(p["iterations"]), tuple(p["reports"]))
            for p in profiles
        },
        reports={r["id"]: ReportEntry(r["id"], r["file"], r["sha256"], int(r["size"])) for r in reports},
    )


# --- §2.1-§2.2: the header -----------------------------------------------------------


@dataclass(frozen=True)
class Slot:
    profile_id: bytes
    salt: bytes
    iterations: int
    wrapped_key: bytes


@dataclass(frozen=True)
class Header:
    raw: bytes
    package_id: bytes
    report_id: bytes
    slots: tuple[Slot, ...]
    iv: bytes
    ciphertext_len: int


class _Cursor:
    def __init__(self, buf: bytes) -> None:
        self.buf = buf
        self.pos = 0

    def take(self, n: int) -> bytes:
        available = len(self.buf) - self.pos >= n
        require(available, HEADER_MALFORMED, "bytes_available")
        out = self.buf[self.pos : self.pos + n]
        self.pos += n
        return out

    def u8(self) -> int:
        return self.take(1)[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]


def parse_header(envelope: bytes) -> tuple[Header, bytes]:
    """Step 2. Returns the header and `ciphertext || tag`."""
    cur = _Cursor(envelope)
    magic = cur.take(4)
    require(magic == MAGIC, HEADER_MALFORMED, "magic")
    version = cur.u8()
    require(version == FORMAT_VERSION, HEADER_MALFORMED, "format_version")
    algorithms = cur.take(len(ALGORITHM_BYTES))
    require(algorithms == ALGORITHM_BYTES, HEADER_MALFORMED, "algorithm_bytes")
    lengths = cur.take(len(LENGTH_BYTES))
    require(lengths == LENGTH_BYTES, HEADER_MALFORMED, "length_bytes")
    package_id = cur.take(PACKAGE_ID_LEN)
    report_id_len = cur.u8()
    require(1 <= report_id_len <= REPORT_ID_MAX, HEADER_MALFORMED, "report_id_length")
    report_id = cur.take(report_id_len)
    require(report_id_ok(report_id), HEADER_MALFORMED, "report_id_bytes")
    slot_count = cur.u8()
    require(1 <= slot_count <= SLOT_COUNT_MAX, HEADER_MALFORMED, "slot_count_range")
    slots: list[Slot] = []
    for _ in range(slot_count):
        profile_id_len = cur.u8()
        require(1 <= profile_id_len <= PROFILE_ID_MAX, HEADER_MALFORMED, "profile_id_length")
        profile_id = cur.take(profile_id_len)
        require(profile_id_ok(profile_id), HEADER_MALFORMED, "profile_id_bytes")
        ascending = not slots or slots[-1].profile_id < profile_id
        require(ascending, HEADER_MALFORMED, "slots_ascending")
        salt = cur.take(SALT_LEN)
        iterations = cur.u32()
        require(ITERATIONS_MIN <= iterations <= ITERATIONS_MAX, HEADER_MALFORMED, "iterations_bounds")
        wrapped_key = cur.take(WRAPPED_LEN)
        slots.append(Slot(profile_id, salt, iterations, wrapped_key))
    iv = cur.take(IV_LEN)
    ciphertext_len = cur.u32()
    require(1 <= ciphertext_len <= CIPHERTEXT_MAX, HEADER_MALFORMED, "ciphertext_len_range")
    end = cur.pos
    rest = len(envelope) - end
    require(rest >= ciphertext_len + TAG_LEN, HEADER_MALFORMED, "ciphertext_available")
    require(rest == ciphertext_len + TAG_LEN, HEADER_MALFORMED, "exact_end")
    header = Header(envelope[:end], package_id, report_id, tuple(slots), iv, ciphertext_len)
    return header, envelope[end : end + ciphertext_len + TAG_LEN]


def build_header(package_id: bytes, report_id: bytes, slots: list[Slot], iv: bytes, ciphertext_len: int) -> bytes:
    """The header of §2.1, slots in ascending `profile_id` order. No
    validation: `seal_report` is the producer's lowest layer, and the
    fixtures of §6.3 need headers the reader refuses."""
    out = bytearray(MAGIC)
    out.append(FORMAT_VERSION)
    out += ALGORITHM_BYTES + LENGTH_BYTES + package_id
    out.append(len(report_id))
    out += report_id
    out.append(len(slots))
    for slot in sorted(slots, key=lambda s: s.profile_id):
        out.append(len(slot.profile_id))
        out += slot.profile_id + slot.salt + struct.pack(">I", slot.iterations) + slot.wrapped_key
    out += iv + struct.pack(">I", ciphertext_len)
    return bytes(out)


# --- §2.4: the payload ---------------------------------------------------------------


def build_payload(totals: bytes, parquet: bytes) -> bytes:
    return PAYLOAD_MAGIC + bytes([PAYLOAD_VERSION]) + struct.pack(">I", len(totals)) + totals + struct.pack(">I", len(parquet)) + parquet


def parse_payload(plain: bytes) -> tuple[bytes, bytes]:
    """Step 9."""
    available = len(plain) >= 9
    require(available, PAYLOAD_MALFORMED, "payload_exact")
    require(plain[:4] == PAYLOAD_MAGIC, PAYLOAD_MALFORMED, "payload_magic")
    require(plain[4] == PAYLOAD_VERSION, PAYLOAD_MALFORMED, "payload_version")
    totals_len = struct.unpack(">I", plain[5:9])[0]
    require(TOTALS_MIN <= totals_len <= TOTALS_MAX, PAYLOAD_MALFORMED, "totals_len_range")
    totals_end = 9 + totals_len
    parquet_len_end = totals_end + 4
    room = len(plain) >= parquet_len_end
    require(room, PAYLOAD_MALFORMED, "payload_exact")
    totals = plain[9:totals_end]
    parquet_len = struct.unpack(">I", plain[totals_end:parquet_len_end])[0]
    require(parquet_len >= PARQUET_MIN, PAYLOAD_MALFORMED, "parquet_len_minimum")
    exact = len(plain) == parquet_len_end + parquet_len
    require(exact, PAYLOAD_MALFORMED, "payload_exact")
    parquet = plain[parquet_len_end:]
    framed = parquet[:4] == PARQUET_MAGIC and parquet[-4:] == PARQUET_MAGIC
    require(framed, PAYLOAD_MALFORMED, "parquet_magic")
    return totals, parquet


# --- §2.3: the cryptography --------------------------------------------------------


def derive_kek(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, KEY_LEN)


@dataclass(frozen=True)
class ProfileKey:
    """A login: the KEK of one profile in one package (§5.1 step 6)."""

    package_id: bytes
    profile_id: str
    kek: bytes


def login(manifest: Manifest, profile_id: str, password: str) -> ProfileKey:
    """Derives the profile's KEK once, as the browser does at login. A profile
    the manifest does not declare is the caller's error, not a refusal."""
    if profile_id not in manifest.profiles:
        raise ValueError(f"profile {profile_id!r} is not in the manifest")
    profile = manifest.profiles[profile_id]
    return ProfileKey(manifest.package_id, profile_id, derive_kek(password, profile.salt, profile.iterations))


# --- §5.1: the reader ----------------------------------------------------------------


def open_report(manifest: Manifest, envelope: bytes, report_id: str, key: ProfileKey) -> tuple[bytes, bytes]:
    """Steps 1 to 9. Returns the totals and the Parquet bytes, or raises
    `Refused`. The manifest is validated already (step 0)."""
    if report_id not in manifest.reports:
        raise ValueError(f"report {report_id!r} is not in the manifest")
    if key.package_id != manifest.package_id:
        raise ValueError("the key was derived for another package: log in again")
    entry = manifest.reports[report_id]
    # 1
    require(len(envelope) == entry.size, INTEGRITY_MISMATCH, "size_equal")
    require(hashlib.sha256(envelope).hexdigest() == entry.sha256, INTEGRITY_MISMATCH, "sha256_equal")
    # 2
    header, sealed = parse_header(envelope)
    # 3
    require(header.package_id == manifest.package_id, IDENTITY_MISMATCH, "package_id_equal")
    require(header.report_id == report_id.encode("ascii"), IDENTITY_MISMATCH, "report_id_equal")
    # 4
    slot_ids = {s.profile_id.decode("ascii") for s in header.slots}
    require(slot_ids == manifest.entitled(report_id), SLOTS_MISMATCH, "slot_set_equal")
    for slot in header.slots:
        profile = manifest.profiles[slot.profile_id.decode("ascii")]
        require(slot.salt == profile.salt, SLOTS_MISMATCH, "slot_salt_equal")
        require(slot.iterations == profile.iterations, SLOTS_MISMATCH, "slot_iterations_equal")
    # 5
    mine = [s for s in header.slots if s.profile_id == key.profile_id.encode("ascii")]
    require(len(mine) == 1, NOT_ENTITLED, "slot_present")
    # 6 is the login; 7
    try:
        dek = aes_key_unwrap(key.kek, mine[0].wrapped_key)
    except InvalidUnwrap:
        raise Refused(UNWRAP_FAILED, None) from None
    # 8
    try:
        plain = AESGCM(dek).decrypt(header.iv, sealed, header.raw)
    except InvalidTag:
        raise Refused(DECRYPT_FAILED, None) from None
    # 9
    return parse_payload(plain)


# --- §5.2: the producer -------------------------------------------------------------


@dataclass(frozen=True)
class SlotInput:
    profile_id: str
    salt: bytes
    iterations: int
    kek: bytes


def seal_report(
    package_id: bytes, report_id: str, slots: list[SlotInput], dek: bytes, iv: bytes, payload: bytes
) -> bytes:
    """The producer's pure layer: every input explicit, nothing drawn, nothing
    validated. The vectors, the sealed fixtures and the reuse tests call it."""
    wrapped = [Slot(s.profile_id.encode("ascii"), s.salt, s.iterations, aes_key_wrap(s.kek, dek)) for s in slots]
    header = build_header(package_id, report_id.encode("ascii"), wrapped, iv, len(payload))
    return header + AESGCM(dek).encrypt(iv, payload, header)


@dataclass(frozen=True)
class DeclaredProfile:
    """One profile of the declaration — the one place the passwords live."""

    id: str
    label: str
    password: str
    reports: tuple[str, ...]


def _validate_declaration(profiles: list[DeclaredProfile], payloads: dict[str, tuple[bytes, bytes]]) -> None:
    ids = [p.id for p in profiles]
    if len(set(ids)) != len(ids):
        raise ValueError("a profile id is repeated")
    for p in profiles:
        raw = _ascii(p.id)
        if raw is None or not 1 <= len(raw) <= PROFILE_ID_MAX or not profile_id_ok(raw):
            raise ValueError(f"profile id {p.id!r} is outside §3")
        if not p.password or not all(0x20 <= ord(c) <= 0x7E for c in p.password):
            raise ValueError(f"the password of {p.id!r} is not printable ASCII (§3)")
        if len(set(p.reports)) != len(p.reports) or not set(p.reports) <= set(payloads):
            raise ValueError(f"profile {p.id!r} lists a report twice or one with no payload")
    for report_id, (totals, parquet) in payloads.items():
        raw = _ascii(report_id)
        if raw is None or not 1 <= len(raw) <= REPORT_ID_MAX or not report_id_ok(raw):
            raise ValueError(f"report id {report_id!r} is outside §3")
        if not any(report_id in p.reports for p in profiles):
            raise ValueError(f"report {report_id!r} is entitled to no profile")
        parsed, value = _totals_json(totals)
        if not parsed or not isinstance(value, dict):
            raise ValueError(f"the control totals of {report_id!r} are not one UTF-8 JSON object with no repeated key (§2.4)")
        parse_payload(build_payload(totals, parquet))
        if len(build_payload(totals, parquet)) > CIPHERTEXT_MAX:
            raise ValueError(f"report {report_id!r} is above the 32 MiB bound")


def _totals_json(raw: bytes) -> tuple[bool, object]:
    """The control totals parsed as CI will parse them (§2.4); a repeated key
    is a failed parse here, not a refusal of the reader."""
    try:
        return _strict_json(raw)
    except Refused:
        return False, None


def _manifest_bytes(package_id: bytes, profiles: list[DeclaredProfile], salts: dict[str, bytes], files: dict[str, bytes]) -> bytes:
    by_report = {}
    for name, data in files.items():
        by_report[name.split(".")[0]] = (name, data)
    manifest = {
        "manifest_version": 1,
        "envelope_format_version": FORMAT_VERSION,
        "package_id": package_id.hex(),
        "profiles": [
            {
                "id": p.id,
                "label": p.label,
                "salt": salts[p.id].hex(),
                "iterations": ITERATIONS,
                "reports": sorted(p.reports, key=_ascii),
            }
            for p in sorted(profiles, key=lambda p: _ascii(p.id))
        ],
        "reports": [
            {"id": rid, "file": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
            for rid, (name, data) in sorted(by_report.items(), key=lambda kv: _ascii(kv[0]))
        ],
    }
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def file_name(report_id: str, envelope: bytes) -> str:
    return f"{report_id}.{hashlib.sha256(envelope).hexdigest()[:16]}.bice"


def encrypt_package(
    profiles: list[DeclaredProfile], payloads: dict[str, tuple[bytes, bytes]]
) -> tuple[bytes, dict[str, bytes]]:
    """One run of the producer (§5.2): the manifest and the envelopes by file
    name. Everything random comes from `secrets`; there is no parameter that
    could make it deterministic. A failure raises and returns nothing: a retry
    is a new call, which draws everything again."""
    _validate_declaration(profiles, payloads)
    package_id = secrets.token_bytes(PACKAGE_ID_LEN)
    salts = {p.id: secrets.token_bytes(SALT_LEN) for p in profiles}
    keks = {p.id: derive_kek(p.password, salts[p.id], ITERATIONS) for p in profiles}
    files: dict[str, bytes] = {}
    for report_id in sorted(payloads, key=_ascii):
        slots = [SlotInput(p.id, salts[p.id], ITERATIONS, keks[p.id]) for p in profiles if report_id in p.reports]
        envelope = seal_report(
            package_id,
            report_id,
            slots,
            secrets.token_bytes(KEY_LEN),
            secrets.token_bytes(IV_LEN),
            build_payload(*payloads[report_id]),
        )
        files[file_name(report_id, envelope)] = envelope
    manifest = _manifest_bytes(package_id, profiles, salts, files)
    check_package(manifest, files, {p.id: p.password for p in profiles}, expected=payloads)
    return manifest, files


# --- §6.4: the package checks ----------------------------------------------------------


def check_package(
    manifest_raw: bytes,
    files: dict[str, bytes],
    passwords: dict[str, str],
    expected: dict[str, tuple[bytes, bytes]] | None = None,
) -> Manifest:
    """The whole matrix and the reuse checks, with the public passwords.
    `expected`, when given, is what each report must open to."""
    manifest = validate_manifest(manifest_raw)
    if set(files) != {r.file for r in manifest.reports.values()}:
        raise ValueError("the files are not exactly the manifest's")
    if set(passwords) != set(manifest.profiles):
        raise ValueError("a password per profile of the manifest is needed")
    keys = {pid: login(manifest, pid, pw) for pid, pw in passwords.items()}
    deks: list[bytes] = []
    ivs: list[bytes] = []
    for report in manifest.reports.values():
        envelope = files[report.file]
        entitled = manifest.entitled(report.id)
        header, _ = parse_header(envelope)
        for pid, key in keys.items():
            if pid in entitled:
                opened = open_report(manifest, envelope, report.id, key)
                if expected is not None and opened != expected[report.id]:
                    raise ValueError(f"{report.id} opens to another payload for {pid}")
            else:
                try:
                    open_report(manifest, envelope, report.id, key)
                except Refused as refusal:
                    if refusal.code != NOT_ENTITLED:
                        raise
                else:  # pragma: no cover - open_report cannot open without a slot
                    raise AssertionError("an unentitled profile opened a report")
                unwrapped = []
                for slot in header.slots:
                    try:
                        aes_key_unwrap(key.kek, slot.wrapped_key)
                    except InvalidUnwrap:
                        continue
                    unwrapped.append(slot)
                require(not unwrapped, UNENTITLED_OPENS, "matrix_closed")
        first = sorted(entitled)[0]
        mine = next(s for s in header.slots if s.profile_id == first.encode("ascii"))
        deks.append(aes_key_unwrap(keys[first].kek, mine.wrapped_key))
        ivs.append(header.iv)
    require(len(set(deks)) == len(deks), DEK_REUSED, "dek_unique")
    require(len(set(ivs)) == len(ivs), IV_REUSED, "iv_unique")
    return manifest


def _raw_deks(manifest: Manifest, files: dict[str, bytes], passwords: dict[str, str]) -> list[bytes]:
    """Every envelope's DEK, unwrapped by an entitled profile with a declared
    password. An envelope none of them opens is `live_unreadable`."""
    keys = {pid: login(manifest, pid, pw) for pid, pw in passwords.items() if pid in manifest.profiles}
    deks = []
    for report in manifest.reports.values():
        header, _ = parse_header(files[report.file])
        dek = None
        for pid in sorted(manifest.entitled(report.id)):
            slot = next((s for s in header.slots if s.profile_id == pid.encode("ascii")), None)
            if pid not in keys or slot is None:
                continue
            try:
                dek = aes_key_unwrap(keys[pid].kek, slot.wrapped_key)
                break
            except InvalidUnwrap:
                continue
        require(dek is not None, LIVE_UNREADABLE, "live_opens")
        deks.append(dek)
    return deks


def check_against_live(
    manifest_raw: bytes,
    files: dict[str, bytes],
    live_manifest_raw: bytes,
    live_files: dict[str, bytes],
    passwords: dict[str, str],
) -> None:
    """§6.4, against the package live: the same `package_id` must be live
    unchanged; a different one shares no DEK, IV or salt with live."""
    manifest = validate_manifest(manifest_raw)
    live = validate_manifest(live_manifest_raw)
    if manifest.package_id == live.package_id:
        same = (
            manifest.profiles == live.profiles
            and manifest.reports == live.reports
            and all(files[r.file] == live_files.get(r.file) for r in manifest.reports.values())
        )
        require(same, PACKAGE_ID_REUSED, "live_unchanged_identical")
        return
    live_deks = set(_raw_deks(live, live_files, passwords))
    deks = set(_raw_deks(manifest, files, passwords))
    require(not (deks & live_deks), DEK_REUSED, "live_dek_fresh")
    ivs = {parse_header(files[r.file])[0].iv for r in manifest.reports.values()}
    live_ivs = {parse_header(live_files[r.file])[0].iv for r in live.reports.values()}
    require(not (ivs & live_ivs), IV_REUSED, "live_iv_fresh")
    salts = {p.salt for p in manifest.profiles.values()}
    live_salts = {p.salt for p in live.profiles.values()}
    require(not (salts & live_salts), SALT_REUSED, "live_salt_fresh")
