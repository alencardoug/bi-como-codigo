"""§4: the view contract, `release/views.json` — its strict loader (§4.1), the
exact fit of a decimal (§4.2, §4.3) and the report contract generated from it
(§4.4).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal

from .. import contract as c
from . import strict_json, CONTRACT_STALE, DECIMAL_REFUSED, VALUE_TYPE, VIEWS_INVALID, Refused

#: The number of views of `consumption` at the pin (PLAN §3.5), and of reports.
VIEW_COUNT = 16

#: §4.4: the source types the views use today, by name, with PostgreSQL's
#: fixed type OID and the type the export writes. A source type outside this
#: list is not exported.
SOURCE_TYPES: dict[str, tuple[int, str]] = {
    "character varying": (1043, "VARCHAR"),
    "text": (25, "VARCHAR"),
    "integer": (23, "INTEGER"),
    "bigint": (20, "BIGINT"),
    "numeric": (1700, "DECIMAL"),
    "boolean": (16, "BOOLEAN"),
    "timestamp with time zone": (1184, "TIMESTAMP WITH TIME ZONE"),
}
TEXT_TYPES = ("character varying", "text")
PRECISION_MAX = c.SUM_PRECISION_MAX  # N106: at most 18, inside N82's sum domain

#: §3 check 8: the four text-form settings, and the collation's fields.
POLICY_KEYS = ("TimeZone", "DateStyle", "IntervalStyle", "extra_float_digits")
COLLATION_KEYS = ("datlocprovider", "datcollate", "datctype", "daticulocale", "daticurules", "datcollversion")
COLLATION_NULLABLE = ("daticulocale", "daticurules", "datcollversion")

_NAME = re.compile(r"[a-z][a-z0-9_]{0,62}")
_ROLE = re.compile(r"[a-z][a-z0-9_]{0,62}")
_REPORT = re.compile(r"P(0[1-9]|1[0-6])")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_MD5 = re.compile(r"[0-9a-f]{32}")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass(frozen=True)
class ViewColumn:
    name: str
    source_type: str
    source_oid: int
    source_typmod: int
    nullable: bool
    precision: int | None = None
    scale: int | None = None
    max_length: int | None = None

    @property
    def export_type(self) -> str:
        base = SOURCE_TYPES[self.source_type][1]
        return f"DECIMAL({self.precision},{self.scale})" if base == "DECIMAL" else base

    @property
    def is_decimal(self) -> bool:
        return self.source_type == "numeric"

    @property
    def is_text(self) -> bool:
        return self.source_type in TEXT_TYPES

    @property
    def is_instant(self) -> bool:
        return self.source_type == "timestamp with time zone"

    @property
    def is_integer(self) -> bool:
        return self.source_type in ("integer", "bigint")


@dataclass(frozen=True)
class View:
    view: str
    report: str
    version: int
    max_rows: int
    may_be_empty: bool
    grain: tuple[str, ...]
    columns: tuple[ViewColumn, ...]

    def column(self, name: str) -> ViewColumn:
        return next(col for col in self.columns if col.name == name)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(col.name for col in self.columns)

    @property
    def sums(self) -> tuple[str, ...]:
        """§8, N107: every column N82 admits — every integer, and every decimal
        of precision up to 18, which §4.2 makes every decimal."""
        return tuple(col.name for col in self.columns if col.is_integer or (col.is_decimal and col.precision <= PRECISION_MAX))


@dataclass(frozen=True)
class Membership:
    member: str
    role: str
    inherit_option: bool
    set_option: bool


@dataclass(frozen=True)
class Provenance:
    built_from_commit: str
    invocation_id: str
    sequence: int


@dataclass(frozen=True)
class Build:
    provenance: Provenance
    policy: dict[str, str]
    collation: dict[str, str | None]
    witness: dict[str, tuple[int, str]]  # view -> (rows, md5)


@dataclass(frozen=True)
class ViewContract:
    contract_version: int
    login: str
    can_login: dict[str, bool]  # the login and every role it reaches
    memberships: tuple[Membership, ...]
    pin: str
    metadata_blob: str
    builds: tuple[Build, ...]
    views: tuple[View, ...]

    def by_view(self) -> dict[str, View]:
        return {v.view: v for v in self.views}

    def by_report(self) -> dict[str, View]:
        return {v.report: v for v in self.views}


# --- §4.1: the strict loader --------------------------------------------------------------


def _bad() -> Refused:
    return Refused(VIEWS_INVALID)


def _obj(value: object, keys: set[str]) -> dict:
    """An object with exactly these keys: every key required, none unknown."""
    if not isinstance(value, dict) or set(value) != keys:
        raise _bad()
    return value


def _int(value: object, minimum: int) -> int:
    if type(value) is not int or value < minimum:  # never a boolean, never a float
        raise _bad()
    return value


def _bool(value: object) -> bool:
    if type(value) is not bool:
        raise _bad()
    return value


def _str(value: object, pattern: re.Pattern | None = None) -> str:
    if not isinstance(value, str) or not value or (pattern is not None and not pattern.fullmatch(value)):
        raise _bad()
    return value


def _list(value: object, nonempty: bool = True) -> list:
    if not isinstance(value, list) or (nonempty and not value):
        raise _bad()
    return value


def _column(raw: object) -> ViewColumn:
    if not isinstance(raw, dict) or "source_type" not in raw:
        raise _bad()
    source_type = raw["source_type"]
    if source_type not in SOURCE_TYPES:
        raise _bad()
    keys = {"name", "source_type", "source_oid", "source_typmod", "nullable"}
    if source_type == "numeric":
        keys |= {"precision", "scale"}
    elif source_type in TEXT_TYPES:
        keys |= {"max_length"}
    body = _obj(raw, keys)
    oid = _int(body["source_oid"], 1)
    if oid != SOURCE_TYPES[source_type][0]:
        raise _bad()
    column = ViewColumn(
        name=_str(body["name"], _NAME),
        source_type=source_type,
        source_oid=oid,
        source_typmod=_int(body["source_typmod"], -1),
        nullable=_bool(body["nullable"]),
        precision=_int(body["precision"], 1) if "precision" in body else None,
        scale=_int(body["scale"], 0) if "scale" in body else None,
        max_length=_int(body["max_length"], 1) if "max_length" in body else None,
    )
    if column.is_decimal and (column.precision > PRECISION_MAX or column.scale > column.precision):
        raise _bad()
    return column


def _view(raw: object) -> View:
    body = _obj(raw, {"view", "report", "version", "max_rows", "may_be_empty", "grain", "columns"})
    columns = tuple(_column(col) for col in _list(body["columns"]))
    names = [col.name for col in columns]
    if len(set(names)) != len(names):
        raise _bad()
    grain = tuple(_str(g, _NAME) for g in _list(body["grain"]))
    if len(set(grain)) != len(grain) or any(g not in names for g in grain):
        raise _bad()
    if any(next(col for col in columns if col.name == g).nullable for g in grain):
        raise _bad()  # a grain column is never nullable
    return View(
        view=_str(body["view"], _NAME),
        report=_str(body["report"], _REPORT),
        version=_int(body["version"], 1),
        max_rows=_int(body["max_rows"], 1),
        may_be_empty=_bool(body["may_be_empty"]),
        grain=grain,
        columns=columns,
    )


def _build(raw: object) -> Build:
    body = _obj(raw, {"provenance", "policy", "collation", "witness"})
    prov = _obj(body["provenance"], {"built_from_commit", "invocation_id", "sequence"})
    policy = _obj(body["policy"], set(POLICY_KEYS))
    collation = _obj(body["collation"], set(COLLATION_KEYS))
    for k in COLLATION_KEYS:
        if not (collation[k] is None and k in COLLATION_NULLABLE):
            _str(collation[k])
    witness: dict[str, tuple[int, str]] = {}
    for entry in _list(body["witness"]):
        item = _obj(entry, {"view", "rows", "md5"})
        name = _str(item["view"], _NAME)
        if name in witness:
            raise _bad()  # each view exactly once
        witness[name] = (_int(item["rows"], 0), _str(item["md5"], _MD5))
    return Build(
        Provenance(_str(prov["built_from_commit"], _COMMIT), _str(prov["invocation_id"], _UUID), _int(prov["sequence"], 0)),
        {k: _str(policy[k]) for k in POLICY_KEYS},
        {k: collation[k] for k in COLLATION_KEYS},
        witness,
    )


def load(raw: bytes) -> ViewContract:
    """`release/views.json`, strictly (§4.1): duplicate keys refused, every key
    required and typed, no unknown key, and its bounds checked."""
    ok, data = strict_json(raw)
    if not ok:
        raise _bad()
    top = _obj(data, {"about", "contract_version", "login", "roles", "pin", "metadata_blob", "accepted_builds", "views"})
    _str(top["about"])
    login = _str(top["login"], _ROLE)
    roles = _obj(top["roles"], {"can_login", "memberships"})
    can_login: dict[str, bool] = {}
    for entry in _list(roles["can_login"]):
        item = _obj(entry, {"role", "rolcanlogin"})
        name = _str(item["role"], _ROLE)
        if name in can_login:
            raise _bad()
        can_login[name] = _bool(item["rolcanlogin"])
    memberships = []
    for entry in _list(roles["memberships"], nonempty=False):
        item = _obj(entry, {"member", "role", "inherit_option", "set_option"})
        memberships.append(Membership(_str(item["member"], _ROLE), _str(item["role"], _ROLE), _bool(item["inherit_option"]), _bool(item["set_option"])))
    if len({(m.member, m.role) for m in memberships}) != len(memberships):
        raise _bad()
    reached = _closure(login, memberships)
    if set(can_login) != reached | {login} or any(m.member not in reached | {login} for m in memberships):
        raise _bad()  # the closure is connected, and every role in it is declared
    views = tuple(_view(v) for v in _list(top["views"]))
    if len(views) != VIEW_COUNT or len({v.view for v in views}) != VIEW_COUNT or len({v.report for v in views}) != VIEW_COUNT:
        raise _bad()
    builds = tuple(_build(b) for b in _list(top["accepted_builds"]))
    provenances = [b.provenance for b in builds]
    if len(set(provenances)) != len(provenances):
        raise _bad()
    for build in builds:
        if set(build.witness) != {v.view for v in views}:
            raise _bad()  # a witness entry for each of the views, exactly
        for v in views:
            if v.max_rows < build.witness[v.view][0]:
                raise _bad()
    return ViewContract(
        contract_version=_int(top["contract_version"], 1),
        login=login,
        can_login=can_login,
        memberships=tuple(memberships),
        pin=_str(top["pin"], _COMMIT),
        metadata_blob=_str(top["metadata_blob"], _COMMIT),
        builds=builds,
        views=views,
    )


def _closure(login: str, memberships: list[Membership]) -> set[str]:
    reached: set[str] = set()
    frontier = {login}
    while frontier:
        step = {m.role for m in memberships if m.member in frontier} - reached
        reached |= step
        frontier = step
    return reached


# --- §4.2, §4.3: the exact fit ------------------------------------------------------------


def fit(value: object, precision: int, scale: int, view: str | None = None) -> str:
    """A `Decimal` that fits DECIMAL(precision, scale) exactly, as its
    fixed-point string at that scale; anything else refuses. Computed from the
    decimal's own digits and exponent: no arithmetic, so no context rounds.
    Negative zero becomes zero; trailing zeros are not digits."""
    if type(value) is not Decimal:
        raise Refused(VALUE_TYPE, view, "decimals")
    if not value.is_finite():
        raise Refused(DECIMAL_REFUSED, view, "decimals")  # NaN, Infinity, -Infinity, sNaN
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    while exponent < 0 and len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    while len(digits) > 1 and digits[0] == 0:
        digits.pop(0)
    if digits == [0]:
        sign, exponent = 0, 0
    fraction = max(0, -exponent)
    whole = max(0, len(digits) + exponent) if digits != [0] else 0
    if fraction > scale or whole > precision - scale:
        raise Refused(DECIMAL_REFUSED, view, "decimals")
    coefficient = "".join(map(str, digits))
    if exponent >= 0:
        integer_part, fraction_part = coefficient + "0" * exponent, ""
    else:
        coefficient = coefficient.rjust(fraction + 1, "0")
        integer_part, fraction_part = coefficient[:-fraction], coefficient[-fraction:]
    integer_part = integer_part.lstrip("0") or "0"
    fraction_part = fraction_part.ljust(scale, "0")
    return ("-" if sign else "") + integer_part + ("." + fraction_part if scale else "")


# --- §4.4: the generated report contract --------------------------------------------------


def report_contract(views: ViewContract) -> bytes:
    """`release/contract.json`, generated: the reports by code, their columns
    with DuckDB's types, `nullable`, grain, sums and versions."""
    lines = ["{", f'  "contract_version": {views.contract_version},', '  "reports": {']
    reports = sorted(views.views, key=lambda v: v.report)
    for i, v in enumerate(reports):
        lines.append(f'    "{v.report}": {{')
        lines.append(f'      "version": {v.version},')
        lines.append('      "columns": [')
        for j, col in enumerate(v.columns):
            item = json.dumps({"name": col.name, "type": col.export_type, "nullable": col.nullable}, separators=(", ", ": "))
            lines.append("        " + item + ("," if j < len(v.columns) - 1 else ""))
        lines.append("      ],")
        lines.append('      "grain": ' + json.dumps(list(v.grain), separators=(", ", ": ")) + ",")
        lines.append('      "sums": ' + json.dumps(list(v.sums), separators=(", ", ": ")))
        lines.append("    }" + ("," if i < len(reports) - 1 else ""))
    lines += ["  }", "}", ""]
    return "\n".join(lines).encode("utf-8")


def check_generated(views: ViewContract, committed: bytes) -> c.Contract:
    """§4.4: the committed report contract is the generated one, byte for byte,
    and loads under the gate's own strict loader."""
    generated = report_contract(views)
    if committed != generated:
        raise Refused(CONTRACT_STALE)
    return c.load_contract(generated)
