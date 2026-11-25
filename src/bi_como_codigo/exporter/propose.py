"""§4.4, the draft: `export propose` writes a draft of `release/views.json` from
a capture's committed output, M59's profile, the metadata package at the pin
and the catalogue `export catalogue` read. The draft is reviewed in full and
committed by hand; the exporter never writes `views.json` itself.

The bounds it proposes are Claude Code's, for the Owner's review:
`max_rows` and `max_length` are twice what M59 measured; decimals follow N106.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass

from . import strict_json, CATALOGUE_INVALID, VIEWS_INVALID, Refused
from .views import COLLATION_KEYS, POLICY_KEYS, PRECISION_MAX, SOURCE_TYPES, TEXT_TYPES

HEADROOM_ROWS = 2
HEADROOM_LENGTH = 2
HEADROOM_DIGITS = 3  # N106
ABOUT = (
    "The view contract of stage 2.4 (docs/exporter.md §4.1): the 16 views of consumption at the pin, "
    "with their source types as the catalogue gives them, the types the export writes, the grain, the bounds "
    "and the accepted builds with their witness. Drafted by `export propose`, reviewed in full and committed "
    "by hand; release/contract.json is generated from it. Protected, like everything under release/."
)


def _sections(text: str) -> dict[str, list[list[str]]]:
    out: dict[str, list[list[str]]] = {}
    for block in text.split("\n## ")[1:]:
        title, _, body = block.partition("\n")
        out[title.strip()] = list(csv.reader(io.StringIO(body.strip())))
    return out


@dataclass(frozen=True)
class Capture:
    login: str
    provenance: dict
    columns: dict[str, list[tuple[str, str]]]
    fingerprints: dict[str, tuple[int, str]]


def parse_capture(text: str) -> Capture:
    """The committed output of a capture such as M59's (`capture.out.txt`)."""
    s = _sections(text)
    try:
        tx = dict(zip(s["transaction"][0], s["transaction"][1]))
        prov = dict(zip(s["provenance"][0], s["provenance"][1]))
        columns: dict[str, list[tuple[str, str]]] = {}
        for row in s["columns"][1:]:
            view, position, name, typ = row[0], int(row[1]), row[2], row[3]
            cols = columns.setdefault(view, [])
            if position != len(cols) + 1:
                raise ValueError("positions")
            cols.append((name, typ))
        fingerprints = {row[0]: (int(row[1]), row[2]) for row in s["fingerprints"][1:]}
        provenance = {"built_from_commit": prov["built_from_commit"], "invocation_id": prov["invocation_id"], "sequence": int(prov["sequence"])}
        if prov["status"] != "verified":
            raise ValueError("status")
        return Capture(tx["login"], provenance, columns, fingerprints)
    except (KeyError, IndexError, ValueError):
        raise Refused(VIEWS_INVALID, check="capture") from None


_VIEW_LINE = re.compile(r"([a-z][a-z0-9_]*): (\d+) rows; grain ([a-z0-9_+]+): (\d+) repeated keys, (\d+) with an empty grain cell")
_COL_LINE = re.compile(r"  ([a-z][a-z0-9_]*) \(([a-z ]+)\): (\d+) null; (.*)")
_NUMERIC = re.compile(r"integer digits ≤ (\d+), fraction digits ≤ (\d+), both ≤ \d+; \d+ negative; NaN or infinity (\d+)")
_TEXT = re.compile(r"longest (\d+) characters; NUL (\d+)")


def parse_profile(text: str) -> dict[str, dict]:
    """M59's profile (`m59_profile.out.txt`): per view its rows and grain, per
    column its nulls and what bounds its type."""
    views: dict[str, dict] = {}
    current = None
    for line in text.splitlines():
        m = _VIEW_LINE.fullmatch(line)
        if m:
            if int(m[4]) or int(m[5]):
                raise Refused(VIEWS_INVALID, m[1], "grain")
            current = views[m[1]] = {"rows": int(m[2]), "grain": m[3].split("+"), "columns": {}}
            continue
        m = _COL_LINE.fullmatch(line)
        if m and current is not None:
            name, typ, nulls, detail = m[1], m[2], int(m[3]), m[4]
            col = {"type": typ, "nulls": nulls}
            if typ == "numeric":
                n = _NUMERIC.fullmatch(detail)
                if not n or int(n[3]):
                    raise Refused(VIEWS_INVALID, check="profile")
                col["integer_digits"], col["fraction_digits"] = int(n[1]), int(n[2])
            elif typ in TEXT_TYPES:
                n = _TEXT.fullmatch(detail)
                if not n or int(n[2]):
                    raise Refused(VIEWS_INVALID, check="profile")
                col["longest"] = int(n[1])
            current["columns"][name] = col
    return views


def parse_catalogue(raw: bytes) -> dict:
    """What `export catalogue` wrote, strictly enough to draft from."""
    ok, data = strict_json(raw)
    keys = {"catalogue_version", "login", "provenance", "memberships", "can_login", "views", "defaults", "encodings", "collation", "collation_actual_version"}
    if not ok or not isinstance(data, dict) or set(data) != keys or data["catalogue_version"] != 1:
        raise Refused(CATALOGUE_INVALID)
    if set(data["defaults"]) != set(POLICY_KEYS) or set(data["collation"]) != set(COLLATION_KEYS):
        raise Refused(CATALOGUE_INVALID)
    return data


def propose(capture: Capture, profile: dict[str, dict], package: dict, catalogue: dict, pin: str, metadata_blob: str) -> dict:
    """The draft, as an object; every disagreement between the inputs refuses."""
    mapping = {body["view"].removeprefix("consumption."): code for code, body in package["questions"].items()}
    if set(mapping) != set(capture.columns) or set(profile) != set(capture.columns) or set(capture.fingerprints) != set(capture.columns):
        raise Refused(VIEWS_INVALID, check="inventory")
    if catalogue["login"] != capture.login or catalogue["provenance"] != {**capture.provenance, "status": "verified"}:
        raise Refused(CATALOGUE_INVALID)
    source = {v["view"]: [(c["name"], c["oid"], c["typmod"]) for c in v["columns"]] for v in catalogue["views"]}
    if set(source) != set(capture.columns):
        raise Refused(CATALOGUE_INVALID)
    views = []
    for view in sorted(capture.columns, key=lambda v: mapping[v]):
        prof = profile[view]
        rules = package["view_rules"][f"consumption.{view}"]["columns"]
        grain = [name for name, _t in capture.columns[view] if rules[name]["role"] in ("grain", "identity")]
        if sorted(grain) != sorted(prof["grain"]) or prof["rows"] != capture.fingerprints[view][0]:
            raise Refused(VIEWS_INVALID, view, "grain")
        if [n for n, _o, _m in source[view]] != [n for n, _t in capture.columns[view]]:
            raise Refused(CATALOGUE_INVALID, view)
        columns = []
        for (name, typ), (_n, oid, typmod) in zip(capture.columns[view], source[view]):
            if typ not in SOURCE_TYPES or SOURCE_TYPES[typ][0] != oid:
                raise Refused(CATALOGUE_INVALID, view)
            measured = prof["columns"][name]
            col: dict = {"name": name, "source_type": typ, "source_oid": oid, "source_typmod": typmod, "nullable": measured["nulls"] > 0}
            if typ == "numeric":
                scale = measured["fraction_digits"]
                precision = measured["integer_digits"] + HEADROOM_DIGITS + scale
                if precision > PRECISION_MAX:
                    raise Refused(VIEWS_INVALID, view, "decimals")
                col["precision"], col["scale"] = precision, scale
            elif typ in TEXT_TYPES:
                col["max_length"] = max(1, HEADROOM_LENGTH * measured["longest"])
            if name in grain and col["nullable"]:
                raise Refused(VIEWS_INVALID, view, "nulls")
            columns.append(col)
        views.append({
            "view": view,
            "report": mapping[view],
            "version": 1,
            "max_rows": max(1, HEADROOM_ROWS * prof["rows"]),
            "may_be_empty": False,
            "grain": grain,
            "columns": columns,
        })
    return {
        "about": ABOUT,
        "contract_version": 1,
        "login": capture.login,
        "roles": {"can_login": catalogue["can_login"], "memberships": catalogue["memberships"]},
        "pin": pin,
        "metadata_blob": metadata_blob,
        "accepted_builds": [{
            "provenance": capture.provenance,
            "policy": catalogue["defaults"],
            "collation": catalogue["collation"],
            "witness": [{"view": v, "rows": capture.fingerprints[v][0], "md5": capture.fingerprints[v][1]} for v in sorted(capture.fingerprints)],
        }],
        "views": views,
    }


def _line(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def dump(draft: dict) -> bytes:
    """A stable layout for review: one line per column, witness entry and role."""
    out = ["{"]
    out.append(f'  "about": {_line(draft["about"])},')
    out.append(f'  "contract_version": {draft["contract_version"]},')
    out.append(f'  "login": {_line(draft["login"])},')
    out.append('  "roles": {')
    out.append('    "can_login": [' + ", ".join(_line(r) for r in draft["roles"]["can_login"]) + "],")
    out.append('    "memberships": [' + ", ".join(_line(r) for r in draft["roles"]["memberships"]) + "]")
    out.append("  },")
    out.append(f'  "pin": {_line(draft["pin"])},')
    out.append(f'  "metadata_blob": {_line(draft["metadata_blob"])},')
    out.append('  "accepted_builds": [')
    for i, b in enumerate(draft["accepted_builds"]):
        out.append("    {")
        out.append(f'      "provenance": {_line(b["provenance"])},')
        out.append(f'      "policy": {_line(b["policy"])},')
        out.append(f'      "collation": {_line(b["collation"])},')
        out.append('      "witness": [')
        out += [f"        {_line(w)}" + ("," if j < len(b["witness"]) - 1 else "") for j, w in enumerate(b["witness"])]
        out.append("      ]")
        out.append("    }" + ("," if i < len(draft["accepted_builds"]) - 1 else ""))
    out.append("  ],")
    out.append('  "views": [')
    for i, v in enumerate(draft["views"]):
        out.append("    {")
        for key in ("view", "report", "version", "max_rows", "may_be_empty", "grain"):
            out.append(f'      "{key}": {_line(v[key])},')
        out.append('      "columns": [')
        out += [f"        {_line(col)}" + ("," if j < len(v["columns"]) - 1 else "") for j, col in enumerate(v["columns"])]
        out.append("      ]")
        out.append("    }" + ("," if i < len(draft["views"]) - 1 else ""))
    out.append("  ]")
    out.append("}")
    return ("\n".join(out) + "\n").encode("utf-8")
