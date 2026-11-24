"""§9: the receipt, `run.json` — a fixed schema, read back strictly: every
field required, typed and allow-listed, no free text from a driver or an
exception, and no value of any row. `export evidence` writes Git's copy from
it, and refuses an incomplete or ill-typed one before writing anything.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re

from . import (
    strict_json,
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
)
from .views import COLLATION_KEYS, POLICY_KEYS, VIEW_COUNT

VERSION = 1
FACT_ORDER = (FACT_TRANSACTION, FACT_PROVENANCE, FACT_LOGIN, FACT_ROLES, FACT_INVENTORY, FACT_ACCESS, FACT_SCHEMA, FACT_POLICY)
PHASES = ("connect", "facts", "read", "checks", "write", "read_back", "seal", "candidate")
DECLARATIONS = (
    "release/views.json",
    "release/contract.json",
    "release/profiles.json",
    "release/public_values.json",
    "release/include.txt",
    "release/media_types.txt",
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SHA1 = re.compile(r"[0-9a-f]{40}")
_MD5 = re.compile(r"[0-9a-f]{32}")
_NAME = re.compile(r"[a-z][a-z0-9_]{0,62}")
_REPORT = re.compile(r"P(0[1-9]|1[0-6])")
_FILE = re.compile(r"P(0[1-9]|1[0-6])\.[0-9a-f]{16}\.bice")
_PATH = re.compile(r"[A-Za-z0-9._/-]{1,255}")
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z")


def _instant(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def build(*, views, metadata, read, settings, per_view, envelopes, candidate, declarations, phases) -> dict:
    return {
        "receipt_version": VERSION,
        "identity": {"pin": views.pin, "metadata_blob": metadata.blob, "metadata_sha256": metadata.sha256},
        "read": {
            "read_at": _instant(read.read_at),
            "provenance": read.provenance,
            "metadata_provenance": metadata.provenance,
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
    return (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# --- the strict reader ----------------------------------------------------------------------


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


def _int(value, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise _bad()
    return value


def _bool(value) -> bool:
    if type(value) is not bool:
        raise _bad()
    return value


def _list(value) -> list:
    if not isinstance(value, list):
        raise _bad()
    return value


def _json_value(value, depth: int = 0) -> None:
    """The compared values of a fact: names, booleans, integers and nulls, in
    lists and objects — never a float, never long free text."""
    if depth > 6:
        raise _bad()
    if value is None or type(value) in (bool, int):
        return
    if isinstance(value, str):
        if len(value) > 255 or any(ch in value for ch in "\x00\n\r"):
            raise _bad()
        return
    if isinstance(value, list):
        for item in value:
            _json_value(item, depth + 1)
        return
    if isinstance(value, dict):
        for k, item in value.items():
            _json_value(k, depth + 1)
            _json_value(item, depth + 1)
        return
    raise _bad()


def load(raw: bytes) -> dict:
    ok, data = strict_json(raw)
    if not ok:
        raise _bad()
    top = _obj(data, ("receipt_version", "identity", "read", "facts", "views", "envelopes", "candidate", "durations"))
    if top["receipt_version"] != VERSION or type(top["receipt_version"]) is not int:
        raise _bad()
    ident = _obj(top["identity"], ("pin", "metadata_blob", "metadata_sha256"))
    _match(ident["pin"], _SHA1)
    _match(ident["metadata_blob"], _SHA1)
    _match(ident["metadata_sha256"], _SHA256)
    rd = _obj(top["read"], ("read_at", "provenance", "metadata_provenance", "policy", "collation", "tls"))
    _match(rd["read_at"], _INSTANT)
    prov = _obj(rd["provenance"], ("status", "built_from_commit", "invocation_id", "sequence"))
    if prov["status"] != "verified":
        raise _bad()
    _match(prov["built_from_commit"], _SHA1)
    _match(prov["invocation_id"], re.compile(r"[0-9a-f-]{36}"))
    _int(prov["sequence"])
    _json_value(rd["metadata_provenance"])
    policy = _obj(rd["policy"], (*POLICY_KEYS, "server_encoding", "client_encoding"))
    for val in policy.values():
        _json_value(val)
        if not isinstance(val, str):
            raise _bad()
    collation = _obj(rd["collation"], (*COLLATION_KEYS, "actual_version"))
    for val in collation.values():
        if val is not None and not isinstance(val, str):
            raise _bad()
        _json_value(val)
    tls = _obj(rd["tls"], ("sslmode", "root_certificate", "crl"))
    if tls["sslmode"] not in ("disable", "allow", "prefer", "require", "verify-ca", "verify-full"):
        raise _bad()
    _bool(tls["root_certificate"])
    _bool(tls["crl"])
    facts = _list(top["facts"])
    if [f.get("code") if isinstance(f, dict) else None for f in facts] != list(FACT_ORDER):
        raise _bad()
    for f in facts:
        _obj(f, ("code", "passed", "compared"))
        if _bool(f["passed"]) is not True or not isinstance(f["compared"], dict):
            raise _bad()
        _json_value(f["compared"])
    per_view = _list(top["views"])
    if len(per_view) != VIEW_COUNT:
        raise _bad()
    for item in per_view:
        _obj(item, ("view", "report", "rows", "fingerprint", "witness_equal", "reference_digest", "parquet_sha256"))
        _match(item["view"], _NAME)
        _match(item["report"], _REPORT)
        _int(item["rows"])
        _match(item["fingerprint"], _MD5)
        if _bool(item["witness_equal"]) is not True:
            raise _bad()
        _match(item["reference_digest"], _SHA256)
        _match(item["parquet_sha256"], _SHA256)
    if len({i["view"] for i in per_view}) != VIEW_COUNT or len({i["report"] for i in per_view}) != VIEW_COUNT:
        raise _bad()
    envelopes = _list(top["envelopes"])
    if len(envelopes) != VIEW_COUNT:
        raise _bad()
    for item in envelopes:
        _obj(item, ("file", "sha256"))
        _match(item["file"], _FILE)
        _match(item["sha256"], _SHA256)
    cand = _obj(top["candidate"], ("listing_digest", "files", "included", "verify", "collisions_approved", "declarations"))
    _match(cand["listing_digest"], _SHA256)
    for item in _list(cand["files"]):
        _obj(item, ("path", "sha256"))
        _match(item["path"], _PATH)
        _match(item["sha256"], _SHA256)
    for item in _list(cand["included"]):
        _match(item, _PATH)
    runs = _list(cand["verify"])
    if [r.get("live") == "none" if isinstance(r, dict) else None for r in runs] != [True, False]:
        raise _bad()
    for r in runs:
        _obj(r, ("live", "passed"))
        if r["live"] != "none":
            _match(r["live"], _SHA256)
        if _bool(r["passed"]) is not True:
            raise _bad()
    _int(cand["collisions_approved"])
    decl = _obj(cand["declarations"], DECLARATIONS)
    for val in decl.values():
        _match(val, _SHA256)
    durations = _obj(top["durations"], PHASES)
    for val in durations.values():
        if type(val) not in (int, float) or val < 0:
            raise _bad()
    return data
