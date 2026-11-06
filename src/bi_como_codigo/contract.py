"""The package gate of stage 2.2b (docs/package_gate.md): the report contract,
the control totals, the Parquet checked with DuckDB, and the inspection of the
finished artifact for clear report values.

Every refusal is a fixed code with the report id and, at most, a column name
of the contract — both public — and never a decrypted value nor a message of
DuckDB (package_gate §7). The callers re-raise it `from None`.
"""

from __future__ import annotations

import json
import re
import tempfile
import pathlib
from dataclasses import dataclass, field
from decimal import Decimal

from . import envelope as e

# --- the codes (package_gate §2–§6) ----------------------------------------------------

CONTRACT_INVALID = "contract_invalid"
DECLARATIONS_AGREE = "declarations_agree"
INVENTORY_EXACT = "inventory_exact"
ENTITLEMENTS_EXACT = "entitlements_exact"
TOTALS_SHAPE = "totals_shape"
TOTALS_VERSION = "totals_version"
TOTALS_ROWS = "totals_rows"
TOTALS_SUMS = "totals_sums"
SCHEMA_EXACT = "schema_exact"
NOT_NULL = "not_null"
GRAIN_UNIQUE = "grain_unique"
CONTENT_BOUND = "content_bound"
PARQUET_UNREADABLE = "parquet_unreadable"
CLEAR_TOTALS = "clear_totals"
CLEAR_VALUE = "clear_value"
PUBLIC_VALUES_INVALID = "public_values_invalid"


class Refused(Exception):
    """A refusal that names its check, its report and at most a contract column."""

    def __init__(self, code: str, report: str | None = None, column: str | None = None, where: str | None = None):
        self.code, self.report, self.column, self.where = code, report, column, where
        parts = [code] + [f"{k} {v}" for k, v in (("report", report), ("column", column), ("in", where)) if v]
        super().__init__(": ".join(parts[:1]) + (" (" + ", ".join(parts[1:]) + ")" if parts[1:] else ""))


def _strict(raw: bytes) -> tuple[bool, object]:
    """The envelope's strict JSON (§2.4); its duplicate-key refusal is a failed parse here."""
    try:
        return e._strict_json(raw)
    except e.Refused:
        return False, None


# --- §2: the contract --------------------------------------------------------------------

_INTEGER_TYPES = ("SMALLINT", "INTEGER", "BIGINT")
_PLAIN_TYPES = ("VARCHAR", "BOOLEAN", *_INTEGER_TYPES, "DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE")
_DECIMAL = re.compile(r"DECIMAL\(([1-9][0-9]?),([0-9][0-9]?)\)")
_COLUMN = re.compile(r"[a-z][a-z0-9_]{0,62}")
SUM_PRECISION_MAX = 18  # N82


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    nullable: bool

    @property
    def decimal(self) -> tuple[int, int] | None:
        m = _DECIMAL.fullmatch(self.type)
        return (int(m[1]), int(m[2])) if m else None

    @property
    def scale(self) -> int:
        d = self.decimal
        return d[1] if d else 0

    @property
    def numeric(self) -> bool:
        return self.type in _INTEGER_TYPES or self.decimal is not None


@dataclass(frozen=True)
class Report:
    id: str
    version: int
    columns: tuple[Column, ...]
    grain: tuple[str, ...]
    sums: tuple[str, ...]

    def column(self, name: str) -> Column:
        return next(c for c in self.columns if c.name == name)


@dataclass(frozen=True)
class Contract:
    version: int
    reports: dict[str, Report]


def _type_ok(text: object) -> bool:
    if not isinstance(text, str):
        return False
    if text in _PLAIN_TYPES:
        return True
    m = _DECIMAL.fullmatch(text)
    return bool(m) and 1 <= int(m[1]) <= 38 and int(m[2]) <= int(m[1])


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def load_contract(raw: bytes) -> Contract:
    """`release/contract.json`, read strictly (package_gate §2.1)."""
    ok, data = _strict(raw)
    if not ok or not isinstance(data, dict) or set(data) != {"contract_version", "reports"}:
        raise Refused(CONTRACT_INVALID)
    if not _positive_int(data["contract_version"]) or not isinstance(data["reports"], dict) or not data["reports"]:
        raise Refused(CONTRACT_INVALID)
    reports: dict[str, Report] = {}
    for rid, body in data["reports"].items():
        if not e.report_id_ok(rid.encode("ascii", "replace")) or not isinstance(body, dict):
            raise Refused(CONTRACT_INVALID, rid if isinstance(rid, str) else None)
        if set(body) != {"version", "columns", "grain", "sums"} or not _positive_int(body["version"]):
            raise Refused(CONTRACT_INVALID, rid)
        cols = body["columns"]
        if not isinstance(cols, list) or not cols:
            raise Refused(CONTRACT_INVALID, rid)
        columns = []
        for c in cols:
            if not isinstance(c, dict) or set(c) != {"name", "type", "nullable"}:
                raise Refused(CONTRACT_INVALID, rid)
            if not isinstance(c["name"], str) or not _COLUMN.fullmatch(c["name"]) or not _type_ok(c["type"]) or not isinstance(c["nullable"], bool):
                raise Refused(CONTRACT_INVALID, rid)
            columns.append(Column(c["name"], c["type"], c["nullable"]))
        names = [c.name for c in columns]
        if len(set(names)) != len(names):
            raise Refused(CONTRACT_INVALID, rid)
        grain, sums = body["grain"], body["sums"]
        if not isinstance(grain, list) or not grain or not isinstance(sums, list):
            raise Refused(CONTRACT_INVALID, rid)
        if any(not isinstance(g, str) or g not in names for g in grain) or len(set(grain)) != len(grain):
            raise Refused(CONTRACT_INVALID, rid)
        if any(next(c for c in columns if c.name == g).nullable for g in grain):
            raise Refused(CONTRACT_INVALID, rid)
        if any(not isinstance(s, str) or s not in names for s in sums) or len(set(sums)) != len(sums):
            raise Refused(CONTRACT_INVALID, rid)
        for s in sums:
            col = next(c for c in columns if c.name == s)
            d = col.decimal
            if not (col.type in _INTEGER_TYPES or (d is not None and d[0] <= SUM_PRECISION_MAX)):
                raise Refused(CONTRACT_INVALID, rid, s)  # N82: only what DuckDB sums without overflow
        reports[rid] = Report(rid, body["version"], tuple(columns), tuple(grain), tuple(sums))
    return Contract(data["contract_version"], reports)


def declarations_agree(contract: Contract, entitled: dict[str, set[str]]) -> None:
    """§2.2, step 1: the two trusted declarations name the same reports."""
    if set(contract.reports) != set().union(*entitled.values()):
        raise Refused(DECLARATIONS_AGREE)


def inventory_exact(contract: Contract, manifest_reports: set[str]) -> None:
    """§2.2, step 2: the package holds exactly the contract's reports."""
    if manifest_reports != set(contract.reports):
        raise Refused(INVENTORY_EXACT)


def entitlements_exact(manifest_map: dict[str, set[str]], declared_map: dict[str, set[str]]) -> None:
    """§2.2, step 3: each profile, with its reports, as release/profiles.json declares it."""
    if manifest_map != declared_map:
        raise Refused(ENTITLEMENTS_EXACT)


def load_public_values(raw: bytes) -> set[str]:
    """`release/public_values.json`: values public by design, each with its reason (§6)."""
    ok, data = _strict(raw)
    if not ok or not isinstance(data, dict) or set(data) != {"about", "values"} or not isinstance(data["values"], list):
        raise Refused(PUBLIC_VALUES_INVALID)
    out = set()
    for item in data["values"]:
        if not isinstance(item, dict) or set(item) != {"value", "reason"}:
            raise Refused(PUBLIC_VALUES_INVALID)
        if not isinstance(item["value"], str) or not item["value"] or not isinstance(item["reason"], str) or not item["reason"].strip():
            raise Refused(PUBLIC_VALUES_INVALID)
        out.add(item["value"])
    return out


# --- §3: the control totals ----------------------------------------------------------------

_CANONICAL = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?")


def canonical_ok(text: str, scale: int) -> bool:
    """§3: an optional `-`, no leading zero but a lone `0`, exactly `scale`
    digits after the point, no point for scale 0, no `-` on zero."""
    m = _CANONICAL.fullmatch(text)
    if not m:
        return False
    fraction = m[2]
    if scale == 0 and fraction is not None:
        return False
    if scale > 0 and (fraction is None or len(fraction) - 1 != scale):
        return False
    return not (text.startswith("-") and Decimal(text) == 0)


def parse_totals(raw: bytes, contract: Contract, report: Report) -> dict:
    """§3: the totals object, strictly, before any comparison with the data."""
    ok, data = _strict(raw)
    if not ok or not isinstance(data, dict) or set(data) != {"contract_version", "report_version", "rows", "sums"}:
        raise Refused(TOTALS_SHAPE, report.id)
    rows, sums = data["rows"], data["sums"]
    if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0 or not isinstance(sums, dict):
        raise Refused(TOTALS_SHAPE, report.id)
    if any(not isinstance(v, str) for v in sums.values()):
        raise Refused(TOTALS_SHAPE, report.id)
    if data["contract_version"] != contract.version or data["report_version"] != report.version:
        raise Refused(TOTALS_VERSION, report.id)
    if set(sums) != set(report.sums):
        raise Refused(TOTALS_SUMS, report.id)
    for name, value in sums.items():
        if not canonical_ok(value, report.column(name).scale):
            raise Refused(TOTALS_SUMS, report.id, name)
    return data


# --- §4: the Parquet, with DuckDB ----------------------------------------------------------

#: §4, step 6: UTF-8 bytes of every VARCHAR together, and cells, before any
#: value leaves DuckDB.
CONTENT_BYTES_MAX = 64 * 1024 * 1024
CELLS_MAX = 10_000_000
MEMORY_LIMIT = "512MB"


@dataclass
class Values:
    """What a report holds, as the inspection of §6 searches it."""

    report: str
    totals_raw: bytes
    texts: set[str] = field(default_factory=set)
    numbers: set[str] = field(default_factory=set)


def _connect():
    import duckdb

    con = duckdb.connect(":memory:", config={
        "autoinstall_known_extensions": False,
        "autoload_known_extensions": False,
        "threads": 1,
        "memory_limit": MEMORY_LIMIT,
    })
    con.execute("SET TimeZone = 'UTC'")
    con.execute("SET lock_configuration = true")
    return con


def _q(name: str) -> str:
    return '"' + name + '"'  # names come from the contract, `[a-z][a-z0-9_]*`


def check_payload(contract: Contract, report: Report, totals_raw: bytes, parquet: bytes) -> Values:
    """§3 and §4 for one opened report. Any failure of DuckDB is
    `parquet_unreadable`, with no message (§7)."""
    totals = parse_totals(totals_raw, contract, report)
    with tempfile.TemporaryDirectory(prefix="bice-gate-") as tmp:
        path = pathlib.Path(tmp) / "report.parquet"
        path.write_bytes(parquet)
        try:
            con = _connect()
            con.execute(f"CREATE VIEW t AS SELECT * FROM read_parquet('{path.as_posix()}')")
            return _check(con, report, totals, totals_raw)
        except Refused:
            raise
        except Exception:
            raise Refused(PARQUET_UNREADABLE, report.id) from None


def _check(con, report: Report, totals: dict, totals_raw: bytes) -> Values:
    schema = [(row[0], row[1]) for row in con.execute("DESCRIBE SELECT * FROM t").fetchall()]
    if schema != [(c.name, c.type) for c in report.columns]:
        raise Refused(SCHEMA_EXACT, report.id)
    for c in report.columns:
        if not c.nullable and con.execute(f"SELECT count(*) FILTER (WHERE {_q(c.name)} IS NULL) FROM t").fetchone()[0]:
            raise Refused(NOT_NULL, report.id, c.name)
    grain = ", ".join(_q(g) for g in report.grain)
    rows, distinct = con.execute(f"SELECT count(*), count(DISTINCT ({grain})) FROM t").fetchone()
    if rows != distinct:
        raise Refused(GRAIN_UNIQUE, report.id)
    if totals["rows"] != rows:
        raise Refused(TOTALS_ROWS, report.id)
    for name in report.sums:
        scale = report.column(name).scale
        got = con.execute(f"SELECT CAST(CAST(COALESCE(SUM({_q(name)}), 0) AS DECIMAL(38,{scale})) AS VARCHAR) FROM t").fetchone()[0]
        if totals["sums"][name] != got:
            raise Refused(TOTALS_SUMS, report.id, name)
    texts = [c for c in report.columns if c.type == "VARCHAR"]
    content = sum(con.execute(f"SELECT COALESCE(SUM(octet_length(encode({_q(c.name)}))), 0) FROM t").fetchone()[0] for c in texts)
    if content > CONTENT_BYTES_MAX or rows * len(report.columns) > CELLS_MAX:
        raise Refused(CONTENT_BOUND, report.id)
    values = Values(report.id, totals_raw)
    values.numbers.add(str(rows))
    values.numbers.update(totals["sums"].values())
    for c in report.columns:
        if c.type == "BOOLEAN":
            continue  # two values, not a figure (§11)
        found = [v for (v,) in con.execute(f"SELECT DISTINCT CAST({_q(c.name)} AS VARCHAR) FROM t WHERE {_q(c.name)} IS NOT NULL").fetchall()]
        (values.numbers if c.numeric else values.texts).update(found)
    return values


# --- §6: the inspection for clear report values --------------------------------------------


def significant_digits(canonical: str) -> int:
    whole = canonical.lstrip("-").split(".")[0].lstrip("0")
    return len(whole)


def eligible_number(canonical: str) -> bool:
    """§6: three or more significant digits, or a non-zero fraction."""
    fraction = canonical.split(".")[1] if "." in canonical else ""
    return significant_digits(canonical) >= 3 or fraction.strip("0") != ""


def spellings(canonical: str) -> list[str]:
    """§6: canonical; Brazilian, `.` grouping thousands and `,` before the
    fraction; and `,` before the fraction with no grouping."""
    sign = "-" if canonical.startswith("-") else ""
    whole, _, fraction = canonical.lstrip("-").partition(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    grouped = ".".join([whole, *groups])
    tail = ("," + fraction) if fraction else ""
    out = [canonical, sign + grouped + tail, sign + canonical.lstrip("-").replace(".", ",")]
    return list(dict.fromkeys(out))


def needles(values: list[Values], public: set[str]) -> list[tuple[str, bytes]]:
    """What §6 searches: (code, bytes), the totals first."""
    found: list[tuple[str, bytes]] = [(CLEAR_TOTALS, v.totals_raw) for v in values]
    seen: set[bytes] = set()
    for v in values:
        for text in sorted(v.texts):
            if len(text) >= 3 and text not in public:
                found.append((CLEAR_VALUE, text.encode("utf-8")))
        for number in sorted(v.numbers):
            if eligible_number(number) and number not in public:
                found.extend((CLEAR_VALUE, s.encode("utf-8")) for s in spellings(number))
    return [(code, b) for code, b in found if not (b in seen or seen.add(b))]


def inspect(haystacks: dict[str, bytes], values: list[Values], public: set[str]) -> None:
    """No haystack — a non-envelope file of deploy/, or for the manifest its
    labels only (N83) — holds a needle. Names the file, never the value."""
    search = needles(values, public)
    for rel in sorted(haystacks):
        data = haystacks[rel]
        for code, needle in search:
            if needle in data:
                raise Refused(code, None, None, rel)


def manifest_labels(manifest: e.Manifest) -> bytes:
    """N83: the manifest's only free text, its profile labels."""
    return "\n".join(p.label for p in manifest.profiles.values()).encode("utf-8")


def load(root: pathlib.Path) -> tuple[Contract, set[str]]:
    contract = load_contract((root / "release" / "contract.json").read_bytes())
    public = load_public_values((root / "release" / "public_values.json").read_bytes())
    return contract, public


def totals_object(contract: Contract, report: Report, rows: int, sums: dict[str, str]) -> bytes:
    """The totals as the exporter writes them (§3) — for the fixtures."""
    return json.dumps({"contract_version": contract.version, "report_version": report.version, "rows": rows,
                       "sums": {k: sums[k] for k in report.sums}}, separators=(",", ":")).encode("utf-8")
