"""§9: the receipt, `run.json` — a fixed schema, read back strictly against the
view contract it was made under: every field required, typed and allow-listed,
and every value either fixed, a digest, a count within its bound, or equal to
what the contract and the accepted build declare (XIMPL-1-02). Nothing in it is
free text — not from a driver, an exception, the metadata package, or a row.
`export evidence` writes Git's copy from it, and refuses an incomplete,
ill-typed or inconsistent one before writing anything.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import pathlib
import re

from .. import release
from . import (
    FACT_ACCESS,
    FACT_INVENTORY,
    FACT_LOGIN,
    FACT_POLICY,
    FACT_PROVENANCE,
    FACT_ROLES,
    FACT_SCHEMA,
    FACT_TRANSACTION,
    RECEIPT_INVALID,
    Refused,
    strict_json,
)
from .views import VIEW_COUNT, ViewContract

VERSION = 1
FACT_ORDER = (FACT_TRANSACTION, FACT_PROVENANCE, FACT_LOGIN, FACT_ROLES, FACT_INVENTORY, FACT_ACCESS, FACT_SCHEMA, FACT_POLICY)
PHASES = ("connect", "facts", "read", "checks", "write", "read_back", "seal", "candidate")
DURATION_MAX = 7 * 24 * 3600.0
DECLARATIONS = (
    "release/views.json",
    "release/contract.json",
    "release/profiles.json",
    "release/public_values.json",
    "release/include.txt",
    "release/media_types.txt",
)
TABLE_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
SSLMODES = ("disable", "allow", "prefer", "require", "verify-ca", "verify-full")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FILE = re.compile(r"(P(?:0[1-9]|1[0-6]))\.[0-9a-f]{16}\.bice")
_PATH = re.compile(r"[A-Za-z0-9._/-]{1,255}")
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z")


def canonical_sha256(value: object) -> str:
    """A digest of a JSON value that the receipt may not carry as text."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _instant(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def build(*, views, metadata, read, settings, per_view, envelopes, candidate, declarations, phases) -> dict:
    return {
        "receipt_version": VERSION,
        "identity": {"pin": views.pin, "metadata_blob": metadata.blob, "metadata_sha256": metadata.sha256},
        "read": {
            "read_at": _instant(read.read_at),
            "provenance": read.provenance,
            "metadata_provenance_sha256": canonical_sha256(metadata.provenance),
            "policy": read.policy,
            "collation": read.collation,
            "tls": {"sslmode": settings.sslmode, "root_certificate": settings.sslrootcert is not None, "crl": settings.sslcrl is not None},
        },
        "facts": [{"code": f.code, "passed": f.passed, "compared": f.compared} for f in read.facts],
        "views": per_view,
        "envelopes": [{"file": name, "sha256": hashlib.sha256(data).hexdigest()} for name, data in sorted(envelopes.items())],
        "candidate": {**candidate, "declarations": dict(sorted(declarations.items()))},
        "durations": {p: round(float(phases[p]), 3) for p in PHASES},
    }


def dump(body: dict) -> bytes:
    return (json.dumps(body, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


# --- what each fact compares, once it has passed: fixed by the contract and the read ------


def expected_facts(views: ViewContract, provenance: dict, policy: dict, collation: dict) -> list[dict]:
    names = sorted(v.view for v in views.views)
    return [
        {"code": FACT_TRANSACTION, "passed": True, "compared": {"isolation": "repeatable read", "read_only": "on"}},
        {"code": FACT_PROVENANCE, "passed": True, "compared": provenance},
        {"code": FACT_LOGIN, "passed": True, "compared": {"session_user": views.login, "current_user": views.login}},
        {"code": FACT_ROLES, "passed": True, "compared": {
            "memberships": [{"member": m, "role": r, "admin_option": False, "inherit_option": i, "set_option": so}
                            for m, r, i, so in sorted((m.member, m.role, m.inherit_option, m.set_option) for m in views.memberships)],
            "can_login": dict(sorted(views.can_login.items())),
        }},
        {"code": FACT_INVENTORY, "passed": True, "compared": {"views": [{"view": n, "kind": "v"} for n in names]}},
        {"code": FACT_ACCESS, "passed": True, "compared": {
            "views": {n: {"table": {p: p == "SELECT" for p in TABLE_PRIVILEGES}, "any_column": {"INSERT": False, "UPDATE": False},
                          "owner_reachable": False} for n in names},
            "schema": {"USAGE": True, "CREATE": False},
        }},
        {"code": FACT_SCHEMA, "passed": True, "compared": {
            "views": {v.view: [[c.name, c.source_oid, c.source_typmod] for c in v.columns] for v in sorted(views.views, key=lambda x: x.view)},
        }},
        {"code": FACT_POLICY, "passed": True, "compared": {"settings": policy, "collation": collation}},
    ]


# --- the strict reader -----------------------------------------------------------------------


def _parts(path: str) -> tuple[str, ...]:
    return pathlib.PurePosixPath(path).parts


def _bad() -> Refused:
    return Refused(RECEIPT_INVALID)


def _obj(value, keys) -> dict:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise _bad()
    return value


def _match(value, pattern: re.Pattern) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise _bad()
    return value


def _int(value, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise _bad()
    return value


def _same(value, expected) -> None:
    """Equal in value and in JSON type, all the way down: `1` is not `true`."""
    if type(value) is not type(expected):
        raise _bad()
    if isinstance(expected, dict):
        if set(value) != set(expected):
            raise _bad()
        for k in expected:
            _same(value[k], expected[k])
    elif isinstance(expected, list):
        if len(value) != len(expected):
            raise _bad()
        for a, b in zip(value, expected):
            _same(a, b)
    elif value != expected:
        raise _bad()


def load(raw: bytes, views: ViewContract) -> dict:
    """The receipt, strictly, against the view contract it was made under."""
    ok, data = strict_json(raw)
    if not ok:
        raise _bad()
    top = _obj(data, ("receipt_version", "identity", "read", "facts", "views", "envelopes", "candidate", "durations"))
    _same(top["receipt_version"], VERSION)
    ident = _obj(top["identity"], ("pin", "metadata_blob", "metadata_sha256"))
    _same(ident["pin"], views.pin)
    _same(ident["metadata_blob"], views.metadata_blob)
    _match(ident["metadata_sha256"], _SHA256)

    rd = _obj(top["read"], ("read_at", "provenance", "metadata_provenance_sha256", "policy", "collation", "tls"))
    _match(rd["read_at"], _INSTANT)
    _match(rd["metadata_provenance_sha256"], _SHA256)
    prov = _obj(rd["provenance"], ("status", "built_from_commit", "invocation_id", "sequence"))
    matching = [b for b in views.builds
                if (prov.get("built_from_commit"), prov.get("invocation_id"), prov.get("sequence"))
                == (b.provenance.built_from_commit, b.provenance.invocation_id, b.provenance.sequence)]
    if len(matching) != 1:
        raise _bad()
    build_ = matching[0]
    _same(prov, {"status": "verified", "built_from_commit": build_.provenance.built_from_commit,
                 "invocation_id": build_.provenance.invocation_id, "sequence": build_.provenance.sequence})
    policy = {**build_.policy, "server_encoding": "UTF8", "client_encoding": "UTF8"}
    _same(rd["policy"], policy)
    stored = build_.collation["datcollversion"]
    collation = {**build_.collation, "actual_version": stored, "version": "unavailable" if stored is None else "verified"}
    _same(rd["collation"], collation)
    tls = _obj(rd["tls"], ("sslmode", "root_certificate", "crl"))
    if tls["sslmode"] not in SSLMODES or type(tls["root_certificate"]) is not bool or type(tls["crl"]) is not bool:
        raise _bad()

    _same(top["facts"], expected_facts(views, rd["provenance"], policy, collation))

    by_view = views.by_view()
    per_view = top["views"]
    if not isinstance(per_view, list) or len(per_view) != VIEW_COUNT:
        raise _bad()
    seen = set()
    for item in per_view:
        _obj(item, ("view", "report", "rows", "fingerprint", "witness_equal", "reference_digest", "parquet_sha256"))
        v = by_view.get(item["view"])
        if v is None or item["view"] in seen:
            raise _bad()
        seen.add(item["view"])
        rows, md5 = build_.witness[v.view]
        _same([item["report"], item["rows"], item["fingerprint"], item["witness_equal"]], [v.report, rows, md5, True])
        _match(item["reference_digest"], _SHA256)
        _match(item["parquet_sha256"], _SHA256)

    envelopes = top["envelopes"]
    if not isinstance(envelopes, list) or len(envelopes) != VIEW_COUNT:
        raise _bad()
    reports, shas = set(), set()
    for item in envelopes:
        _obj(item, ("file", "sha256"))
        m = _FILE.fullmatch(item["file"]) if isinstance(item["file"], str) else None
        if m is None:
            raise _bad()
        reports.add(m[1])
        shas.add(_match(item["sha256"], _SHA256))
    if reports != {v.report for v in views.views} or len(shas) != VIEW_COUNT:
        raise _bad()

    cand = _obj(top["candidate"], ("commit", "listing_digest", "files", "included", "verify", "collisions_approved", "declarations"))
    _match(cand["commit"], re.compile(r"[0-9a-f]{40}"))  # the rehearsed commit: its names are the inventory
    files = cand["files"]
    if not isinstance(files, list) or not files:
        raise _bad()
    listing = []
    for item in files:
        _obj(item, ("path", "sha256"))
        listing.append((_match(item["path"], _PATH), _match(item["sha256"], _SHA256)))
    if listing != sorted(set(listing), key=lambda item: _parts(item[0])) or len({p for p, _ in listing}) != len(listing):
        raise _bad()  # the gate's own order: by path components, as `release.listing` walks them (XIMPL-2-04)
    _same(cand["listing_digest"], release.canonical_digest(listing))
    deployed = dict(listing)
    if "package/manifest.json" not in deployed:
        raise _bad()
    for item in envelopes:
        if deployed.get(f"package/{item['file']}") != item["sha256"]:
            raise _bad()  # the candidate deployed exactly the sealed envelopes
    sealed = {"package/manifest.json"} | {f"package/{item['file']}" for item in envelopes}
    if {p for p in deployed if p.startswith("package/")} != sealed:
        raise _bad()  # nothing else under package/: no other name can enter the evidence (XIMPL-3-01)
    included = cand["included"]
    if not isinstance(included, list) or [_match(i, _PATH) for i in included] != sorted({f"site/{p}" for p in deployed}, key=_parts):
        raise _bad()
    runs = cand["verify"]
    if not isinstance(runs, list) or len(runs) != 2:
        raise _bad()
    _same(runs[0], {"live": "none", "passed": True})
    _obj(runs[1], ("live", "passed"))
    _match(runs[1]["live"], _SHA256)
    _same(runs[1]["passed"], True)
    approved = _obj(cand["collisions_approved"], ("used", "unused"))
    used = [_int(i, 0, 10_000) for i in approved["used"]] if isinstance(approved["used"], list) else None
    unused = [_int(i, 0, 10_000) for i in approved["unused"]] if isinstance(approved["unused"], list) else None
    if used is None or unused is None or used != sorted(set(used)) or unused != sorted(set(unused)) or set(used) & set(unused):
        raise _bad()
    decl = _obj(cand["declarations"], DECLARATIONS)
    for val in decl.values():
        _match(val, _SHA256)

    durations = _obj(top["durations"], PHASES)
    for val in durations.values():
        if type(val) not in (int, float) or not math.isfinite(val) or not 0 <= val <= DURATION_MAX:
            raise _bad()
    return data
