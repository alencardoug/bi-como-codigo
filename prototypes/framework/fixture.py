"""The fixture of stage 2.3 (docs/framework_prototype.md §2.1).

P01's twelve columns, in their order, with every value invented: 61 months of
3 channels × 60 categories, the gap G, the zero Z and a partial last month of
*k* whole groups. The values are drawn from a recorded seed; the shape is
checked from the rows themselves before anything is sealed; the control
totals are computed here with `decimal`, independently of the gate's DuckDB
query; and the package is sealed with the envelope's producer under the
prototype's own declarations (`release/`).

    uv run --frozen --group prototype python prototypes/framework/fixture.py write --seed 7 --out <dir>

The draw against the candidates' builder outputs (§2.1, steps 1 to 4) is
`draw`, with the collision search given by the caller.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import random
import re
import sys
import tempfile
from collections import defaultdict
from decimal import Decimal, localcontext

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.append(str(REPO / "src"))

from bi_como_codigo import contract as c, envelope as e, release  # noqa: E402

REPORT = "P01"
COLUMNS = (
    "year_month", "year_number", "month_number", "sales_channel_name", "channel_type",
    "root_category_name", "category_name", "order_count", "unit_count",
    "gross_revenue_amount", "discount_amount", "net_revenue_amount",
)

# --- the shape (§2.1) ------------------------------------------------------------------

CHANNELS = {
    "fixture_canal_a": "fixture_tipo_1",
    "fixture_canal_b": "fixture_tipo_1",
    "fixture_canal_c": "fixture_tipo_2",
}
ROOTS = tuple(f"fixture_raiz_{r}" for r in range(1, 6))
CATEGORIES = {root: tuple(f"fixture_cat_{r}_{n:02d}" for n in range(1, 13)) for r, root in enumerate(ROOTS, 1)}
ROOT_OF = {cat: root for root, cats in CATEGORIES.items() for cat in cats}
GROUP = 12
MONTHS = 61
PARTIAL = MONTHS - 1
#: (month index, channel, root): no row at all — the summary's empty cell.
G = (4, "fixture_canal_c", "fixture_raiz_3")
#: (month index, channel, root): discount equal to gross on every row, net 0.00.
Z = (6, "fixture_canal_b", "fixture_raiz_2")
PARTIAL_CHANNELS = ("fixture_canal_a", "fixture_canal_b")
K_VALUES = tuple(range(5, 11))
#: The years a window may start in; the draw moves it when the calendar collides.
START_YEARS = range(2000, 2200)
FILTERS = ("todos", *CHANNELS)
DRAWS_MAX = 1000

#: The partial month's smaller amounts (§2.1), as a property of its rows: at
#: most this many orders per row and this gross revenue per unit.
PARTIAL_ORDERS_MAX = 20_000
PARTIAL_PRICE_MAX = Decimal("120.00")
FULL_PRICE_MAX = Decimal("400.00")

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def row_count(k: int, mutant: bool = False) -> int:
    """60 × 180 − 12 + 12k; the G mutant adds G's 12 rows back."""
    full = PARTIAL * len(CHANNELS) * len(ROOTS) * GROUP
    return full - GROUP + GROUP * k + (GROUP if mutant else 0)


class ShapeError(Exception):
    """The rows are not the shape of §2.1; nothing is sealed."""


@dataclasses.dataclass(frozen=True)
class Measures:
    order_count: int
    unit_count: int
    gross: Decimal
    discount: Decimal
    net: Decimal


Key = tuple[int, str, str]  # (month index, channel, category)


@dataclasses.dataclass
class Fixture:
    seed: int
    start: tuple[int, int]  # (year, month) of the first month
    k: int
    partial: tuple[tuple[str, str], ...]  # the (channel, root) groups of the last month
    cells: dict[Key, Measures]
    mutant: bool = False

    def month(self, index: int) -> tuple[int, int]:
        year, month = self.start
        n = year * 12 + (month - 1) + index
        return n // 12, n % 12 + 1

    def year_month(self, index: int) -> str:
        y, m = self.month(index)
        return f"{y:04d}-{m:02d}"

    def rows(self) -> list[tuple]:
        """In the contract's column order, sorted by the grain."""
        out = []
        for (i, channel, cat), m in self.cells.items():
            y, mo = self.month(i)
            out.append((self.year_month(i), y, mo, channel, CHANNELS[channel], ROOT_OF[cat], cat,
                        m.order_count, m.unit_count, m.gross, m.discount, m.net))
        return sorted(out, key=lambda r: (r[0], r[3], r[6]))

    def describe(self) -> dict:
        return {"seed": self.seed, "start": self.year_month(0), "end": self.year_month(PARTIAL), "k": self.k,
                "partial_groups": [list(g) for g in self.partial], "rows": len(self.cells), "mutant": self.mutant}


def _groups(month: int, partial: tuple[tuple[str, str], ...]) -> list[tuple[str, str]]:
    """The (channel, root) groups a month holds before G is taken out."""
    if month == PARTIAL:
        return list(partial)
    return [(ch, root) for ch in CHANNELS for root in ROOTS]


class _Draw:
    """The random stream of one seed and the values already taken: counts are
    distinct across the fixture, amounts across the three amount columns."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.counts: set[int] = set()
        self.amounts: set[Decimal] = set()

    def measures(self, *, small: bool, zero: bool) -> Measures:
        rng = self.rng
        while True:
            orders = rng.randint(10_000, PARTIAL_ORDERS_MAX if small else 60_000)
            units = rng.randint(orders + orders // 5, min(999_999, orders * 3))
            if {orders, units} & self.counts:
                continue
            gross = Decimal(rng.randint(units * 2_000, units * int((PARTIAL_PRICE_MAX if small else FULL_PRICE_MAX) * 100))).scaleb(-2)
            if zero:
                discount, net = gross, ZERO
                taken = {gross}
            else:
                discount = (gross * rng.randint(100, 1_500) / 10_000).quantize(CENT)
                net = gross - discount
                taken = {gross, discount, net}
                if len(taken) != 3:
                    continue
            if taken & self.amounts:
                continue
            self.counts |= {orders, units}
            self.amounts |= taken
            return Measures(orders, units, gross, discount, net)

    def release(self, m: Measures) -> None:
        self.counts -= {m.order_count, m.unit_count}
        self.amounts -= {m.gross, m.discount, m.net}

    def start(self) -> tuple[int, int]:
        return self.rng.choice(START_YEARS), self.rng.randint(1, 12)

    def partial(self, k: int) -> tuple[tuple[str, str], ...]:
        groups = [(ch, root) for ch in PARTIAL_CHANNELS for root in ROOTS]
        return tuple(sorted(self.rng.sample(groups, k)))


def _fill(fx: Fixture, d: _Draw, month: int, channel: str, root: str) -> None:
    zero = (month, channel, root) == Z
    for cat in CATEGORIES[root]:
        fx.cells[(month, channel, cat)] = d.measures(small=month == PARTIAL, zero=zero)


def generate(seed: int, k: int | None = None, start: tuple[int, int] | None = None) -> tuple[Fixture, _Draw]:
    d = _Draw(seed)
    start = start or d.start()
    k = k if k is not None else d.rng.choice(K_VALUES)
    fx = Fixture(seed, start, k, d.partial(k), {})
    for month in range(MONTHS):
        for channel, root in _groups(month, fx.partial):
            if (month, channel, root) != G:
                _fill(fx, d, month, channel, root)
    _separate_order_sums(fx, d)
    return fx, d


# --- what the page shows, and the sums of order_count it must not show (§2.1, §2.3) ----


def _in_filter(channel: str, f: str) -> bool:
    return f == "todos" or channel == f


def summary(fx: Fixture) -> dict[tuple[str, int, str], tuple[Decimal, int]]:
    """(filter, month, root) → (net, units), summed from the rows of the filter;
    a cell with no row is absent (G)."""
    out: dict[tuple[str, int, str], list] = {}
    for (i, ch, cat), m in fx.cells.items():
        for f in FILTERS:
            if _in_filter(ch, f):
                cell = out.setdefault((f, i, ROOT_OF[cat]), [ZERO, 0])
                cell[0] += m.net
                cell[1] += m.unit_count
    return {key: (net, units) for key, (net, units) in out.items()}


def order_sums(fx: Fixture) -> dict[tuple[str, int, str], int]:
    out: dict[tuple[str, int, str], int] = defaultdict(int)
    for (i, ch, cat), m in fx.cells.items():
        for f in FILTERS:
            if _in_filter(ch, f):
                out[(f, i, ROOT_OF[cat])] += m.order_count
    return dict(out)


def displayed_numbers(fx: Fixture) -> set[Decimal]:
    """Every number the page displays: the detail's native cells and the
    summary's and chart's sums."""
    out: set[Decimal] = set()
    for m in fx.cells.values():
        out |= {Decimal(m.order_count), Decimal(m.unit_count), m.net}
    for net, units in summary(fx).values():
        out |= {net, Decimal(units)}
    return out


def _separate_order_sums(fx: Fixture, d: _Draw, rounds: int = 200) -> None:
    """No sum of `order_count` over a summary cell equals a displayed number:
    a colliding cell has one of its rows redrawn."""
    for _ in range(rounds):
        shown = displayed_numbers(fx)
        sums = order_sums(fx)
        bad = sorted(key for key, s in sums.items() if Decimal(s) in shown)
        if not bad:
            return
        f, i, root = bad[0]
        keys = sorted(k for k in fx.cells if k[0] == i and ROOT_OF[k[2]] == root and _in_filter(k[1], f))
        _redraw(fx, d, d.rng.choice(keys))
    raise ShapeError("the sums of order_count could not be kept apart from the displayed numbers")


def _redraw(fx: Fixture, d: _Draw, key: Key) -> None:
    old = fx.cells[key]
    zero = (key[0], key[1], ROOT_OF[key[2]]) == Z
    fresh = d.measures(small=key[0] == PARTIAL, zero=zero)
    d.release(old)
    fx.cells[key] = fresh


# --- the shape, checked from the rows (§2.1) -------------------------------------------


def check_shape(rows: list[tuple], k: int, *, mutant: bool = False) -> None:
    """Fails before sealing if any property of §2.1 does not hold. Reads only
    the rows, never the generator's state."""
    idx = {name: n for n, name in enumerate(COLUMNS)}

    def col(r, name):
        return r[idx[name]]

    for r in rows:  # the types and forms of each column, before anything is computed from them (PROTO-1-10)
        if len(r) != len(COLUMNS):
            raise ShapeError("a row of the wrong width")
        if not (isinstance(col(r, "year_month"), str) and re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", col(r, "year_month"))):
            raise ShapeError("a year_month that is not YYYY-MM")
        if any(type(col(r, n)) is not int for n in ("year_number", "month_number", "order_count", "unit_count")):
            raise ShapeError("a count or a calendar number that is not an integer")
        if any(not isinstance(col(r, n), str) for n in ("sales_channel_name", "channel_type", "root_category_name", "category_name")):
            raise ShapeError("a text column that is not text")
        if any(not isinstance(col(r, n), Decimal) for n in ("gross_revenue_amount", "discount_amount", "net_revenue_amount")):
            raise ShapeError("an amount that is not a decimal")
    if len(rows) != row_count(k, mutant):
        raise ShapeError(f"{len(rows)} rows, not {row_count(k, mutant)} for k={k}")
    months = sorted({col(r, "year_month") for r in rows})
    if len(months) != MONTHS:
        raise ShapeError(f"{len(months)} months, not {MONTHS}")
    ym = [(int(m[:4]), int(m[5:])) for m in months]
    if any((b[0] * 12 + b[1]) - (a[0] * 12 + a[1]) != 1 for a, b in zip(ym, ym[1:])):
        raise ShapeError("the months are not consecutive")
    month_of = {m: n for n, m in enumerate(months)}
    for r in rows:
        if (col(r, "year_number"), col(r, "month_number")) != ym[month_of[col(r, "year_month")]]:
            raise ShapeError("year_number and month_number disagree with year_month")
        if CHANNELS.get(col(r, "sales_channel_name")) != col(r, "channel_type"):
            raise ShapeError("a channel with the wrong type")
        if ROOT_OF.get(col(r, "category_name")) != col(r, "root_category_name"):
            raise ShapeError("a category under the wrong root")
    grain = [(col(r, "year_month"), col(r, "sales_channel_name"), col(r, "category_name")) for r in rows]
    if len(set(grain)) != len(grain):
        raise ShapeError("the grain repeats")
    groups: dict[tuple[int, str, str], list[tuple]] = defaultdict(list)
    for r in rows:
        groups[(month_of[col(r, "year_month")], col(r, "sales_channel_name"), col(r, "root_category_name"))].append(r)
    if any(len(g) != GROUP for g in groups.values()):
        raise ShapeError("a group that is not whole")
    last = [g for g in groups if g[0] == PARTIAL]
    if any(g[1] == "fixture_canal_c" for g in last) or len(last) != k or k not in K_VALUES:
        raise ShapeError("the partial month is not k whole groups of the first two channels")
    if any(len([g for g in groups if g[0] == i]) != len(CHANNELS) * len(ROOTS) - (G[0] == i and not mutant) for i in range(PARTIAL)):
        raise ShapeError("a full month misses a group other than G")
    for r in (r for g, rs in groups.items() if g[0] == PARTIAL for r in rs):  # the partial month's smaller amounts
        if col(r, "order_count") > PARTIAL_ORDERS_MAX or col(r, "gross_revenue_amount") > col(r, "unit_count") * PARTIAL_PRICE_MAX:
            raise ShapeError("the partial month's amounts are not the smaller ones")
    zeros = set(groups.get(Z, ())) | (set(groups.get(G, ())) if mutant else set())
    if mutant:
        if G not in groups or any(col(r, n) != 0 for r in groups[G] for n in COLUMNS[7:]):
            raise ShapeError("the mutant's G is not 12 rows of zeros")
    elif G in groups:
        raise ShapeError("G holds a row")
    if Z not in groups:
        raise ShapeError("Z is missing")
    for r in groups[Z]:
        if not (col(r, "unit_count") > 0 and col(r, "gross_revenue_amount") > 0
                and col(r, "discount_amount") == col(r, "gross_revenue_amount") and col(r, "net_revenue_amount") == ZERO):
            raise ShapeError("a row of Z is not a zero net from a full discount")
    counts = [col(r, n) for r in rows if r not in zeros or r in groups[Z] for n in ("order_count", "unit_count")]
    if len(set(counts)) != len(counts) or any(not 10_000 <= v <= 999_999 for v in counts):
        raise ShapeError("a count repeats or has fewer than five or more than six digits")
    amounts = []
    for r in rows:
        if r in zeros:
            if r in groups[Z]:
                amounts.append(col(r, "gross_revenue_amount"))
            continue
        amounts += [col(r, n) for n in ("gross_revenue_amount", "discount_amount", "net_revenue_amount")]
    if len(set(amounts)) != len(amounts):
        raise ShapeError("an amount repeats across the amount columns, outside Z's exceptions")
    if any(a.as_tuple().exponent != -2 or len(a.as_tuple().digits) < 5 or a <= 0 for a in amounts):
        raise ShapeError("an amount without two decimals or with fewer than five digits")
    if sum(1 for a in amounts if a.as_tuple().digits[-1] == 0) < 10:
        raise ShapeError("fewer than ten amounts whose fraction ends in 0")
    _check_order_sums(rows, month_of, idx)


def _check_order_sums(rows: list[tuple], month_of: dict[str, int], idx: dict[str, int]) -> None:
    shown: set[Decimal] = set()
    sums: dict[tuple, list] = {}
    orders: dict[tuple, int] = defaultdict(int)
    for r in rows:
        ch, root, i = r[idx["sales_channel_name"]], r[idx["root_category_name"]], month_of[r[idx["year_month"]]]
        shown |= {Decimal(r[idx["order_count"]]), Decimal(r[idx["unit_count"]]), r[idx["net_revenue_amount"]]}
        for f in FILTERS:
            if _in_filter(ch, f):
                cell = sums.setdefault((f, i, root), [ZERO, 0])
                cell[0] += r[idx["net_revenue_amount"]]
                cell[1] += r[idx["unit_count"]]
                orders[(f, i, root)] += r[idx["order_count"]]
    for net, units in sums.values():
        shown |= {net, Decimal(units)}
    if any(Decimal(s) in shown for s in orders.values() if s):
        raise ShapeError("a sum of order_count equals a displayed number")


# --- the G mutant (§2.1, FPROTO-4-06) ---------------------------------------------------


def mutant(fx: Fixture) -> Fixture:
    """G's group filled with 12 rows of zeros."""
    cells = dict(fx.cells)
    month, channel, root = G
    for cat in CATEGORIES[root]:
        cells[(month, channel, cat)] = Measures(0, 0, ZERO, ZERO, ZERO)
    return Fixture(fx.seed, fx.start, fx.k, fx.partial, cells, mutant=True)


# --- the payload and the package (§2.2) -------------------------------------------------


def contract() -> c.Contract:
    return c.load_contract((HERE / "release" / "contract.json").read_bytes())


def parquet(rows: list[tuple]) -> bytes:
    """The rows as a Parquet file written by DuckDB with the contract's types."""
    import duckdb
    import pyarrow as pa

    report = contract().reports[REPORT]
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE t (" + ", ".join(f'"{col.name}" {col.type}' for col in report.columns) + ")")
    if rows:  # through Arrow: executemany takes a minute for 10,000 rows
        source = pa.table({name: [r[n] for r in rows] for n, name in enumerate(COLUMNS)})
        con.register("source", source)
        con.execute("INSERT INTO t SELECT " + ", ".join(f'CAST("{col.name}" AS {col.type})' for col in report.columns) + " FROM source")
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "t.parquet"
        con.execute(f"COPY (SELECT * FROM t ORDER BY year_month, sales_channel_name, category_name) TO '{path.as_posix()}' (FORMAT parquet)")
        return path.read_bytes()


def totals(rows: list[tuple]) -> bytes:
    """§3 of package_gate.md, independently of DuckDB: `decimal` at 60 digits."""
    con = contract()
    report = con.reports[REPORT]
    sums = {}
    with localcontext() as ctx:
        ctx.prec = 60
        for name in report.sums:
            scale = report.column(name).scale
            total = sum((Decimal(r[COLUMNS.index(name)]) for r in rows), Decimal(0))
            sums[name] = f"{total.quantize(Decimal(1).scaleb(-scale)):f}" if scale else str(int(total))
    return c.totals_object(con, report, len(rows), sums)


class SchemaFault(Exception):
    """The schema check itself could not run — not a property of the file."""


def _another_reader_opens(data: bytes) -> bool:
    """PyArrow reads the file's metadata and schema: the witness that bytes
    DuckDB refused are a Parquet after all."""
    import io

    import pyarrow.parquet as pq

    try:
        pq.ParquetFile(io.BytesIO(data)).schema_arrow
        return True
    except Exception:  # noqa: BLE001 — any refusal of the bytes
        return False


def schema_only(data: bytes) -> bool | None:
    """A Parquet with P01's names and types and zero rows: True; one that parses
    otherwise: False; bytes that do not parse as a Parquet: None. A failure of
    the check's own machinery raises `SchemaFault` (PROTO-1-02, PROTO-1-06)."""
    try:
        import duckdb

        report = contract().reports[REPORT]
        tmp = tempfile.TemporaryDirectory()
        path = pathlib.Path(tmp.name) / "f.parquet"
        path.write_bytes(data)
        con = duckdb.connect(":memory:")
    except Exception as error:  # noqa: BLE001
        raise SchemaFault(f"{type(error).__name__}") from None
    try:
        with tmp:
            try:
                schema = [(r[0], r[1]) for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path.as_posix()}')").fetchall()]
                rows = con.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]
            except duckdb.Error as error:
                # Bytes that do not parse are the file's. DuckDB 1.5.6 reports most
                # as invalid input (no magic bytes, a footer length, a file too
                # small, a page that fails to read), but a damaged Thrift footer
                # as its base `Error` (PROTO-4-04): then a second reader decides —
                # bytes PyArrow refuses too are the file's; bytes it reads mean
                # DuckDB's own failure. Memory, I/O, an internal fault, or a file
                # that is no longer the one written are the check's own failure
                # (PROTO-2-03, PROTO-3-04).
                try:
                    intact = path.read_bytes() == data
                except OSError:
                    intact = False
                if not intact:
                    raise SchemaFault(f"the checked file changed: {type(error).__name__}") from None
                if isinstance(error, duckdb.InvalidInputException) or not _another_reader_opens(data):
                    return None
                raise SchemaFault(f"the schema query failed on bytes another reader opens: {type(error).__name__}") from None
    finally:
        con.close()
    return schema == [(col.name, col.type) for col in report.columns] and rows == 0


def payload(fx: Fixture) -> tuple[bytes, bytes]:
    rows = fx.rows()
    check_shape(rows, fx.k, mutant=fx.mutant)
    return totals(rows), parquet(rows)


def _eligible(canonical: str) -> bool:
    """The gate's rule, restated (package_gate §6): three significant digits or
    a non-zero fraction."""
    whole, _, fraction = canonical.lstrip("-").partition(".")
    return len(whole.lstrip("0")) >= 3 or fraction.strip("0") != ""


def _spell(canonical: str) -> list[str]:
    """The three spellings of package_gate §6, restated from the rule, not
    taken from `contract.spellings`: canonical, Brazilian with `.` grouping
    thousands and `,` before the fraction, and `,` before the fraction."""
    whole, _, fraction = canonical.partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    tail = f",{fraction}" if fraction else ""
    return list(dict.fromkeys([canonical, grouped + tail, whole + tail]))


def coverage(fx: Fixture, totals_raw: bytes, parquet_raw: bytes, public: set[str] | None = None) -> int:
    """The coverage assertion (§2.1): `contract.needles` on the payload, under
    the prototype's effective public declarations, holds every eligible
    number's spellings and every text of three characters or more, with no
    public value excluding any, and as many needles as the fixture alone gives
    — the expectation computed from the fixture's rows, its own totals and its
    own spellings (PROTO-1-10). Returns the count."""
    if public is None:
        public = c.load_public_values((HERE / "release" / "public_values.json").read_bytes())
    con = contract()
    values = c.check_payload(con, con.reports[REPORT], totals_raw, parquet_raw)
    got = c.needles([values], public)
    rows = fx.rows()
    texts = {r[n] for r in rows for n in range(len(COLUMNS)) if isinstance(r[n], str)}
    numbers = {str(r[n]) for r in rows for n in range(len(COLUMNS)) if not isinstance(r[n], str)}
    numbers.add(str(len(rows)))
    own_totals = totals(rows)
    numbers |= set(json.loads(own_totals)["sums"].values())
    excluded = sorted(public & (texts | numbers))
    if excluded:
        raise ShapeError(f"coverage: {len(excluded)} fixture values excluded by a public declaration")
    expected = [own_totals] + [t.encode() for t in sorted(texts) if len(t) >= 3]
    expected += [s.encode() for n in sorted(numbers) if _eligible(n) for s in _spell(n)]
    expected = list(dict.fromkeys(expected))
    found = [needle for _, needle in got]
    present = set(found)
    missing = [n for n in expected if n not in present]
    if own_totals != totals_raw or missing or sorted(found) != sorted(expected):
        raise ShapeError(f"coverage: {len(missing)} missing, {len(found)} needles against {len(expected)} expected")
    return len(found)


def seal(totals_raw: bytes, parquet_raw: bytes) -> tuple[bytes, dict[str, bytes]]:
    return e.encrypt_package(release.profiles(HERE), {REPORT: (totals_raw, parquet_raw)})


def write(fx: Fixture, out: pathlib.Path) -> dict:
    """The fixture's record, its clear Parquet and its package, into a fresh
    `out` — under `prototypes/framework/clear/`, never in a candidate's tree."""
    if out.exists():
        raise SystemExit(f"{out} exists: a fixture is written fresh")
    totals_raw, parquet_raw = payload(fx)
    count = coverage(fx, totals_raw, parquet_raw)
    manifest, files = seal(totals_raw, parquet_raw)
    (out / "package").mkdir(parents=True)
    (out / "package" / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (out / "package" / name).write_bytes(data)
    (out / "p01.parquet").write_bytes(parquet_raw)
    (out / "totals.json").write_bytes(totals_raw)
    record = fx.describe() | {
        "needles": count,
        "parquet_sha256": hashlib.sha256(parquet_raw).hexdigest(),
        "package": {name: hashlib.sha256(data).hexdigest() for name, data in {"manifest.json": manifest, **files}.items()},
    }
    (out / "fixture.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


# --- the draw against the builder outputs (§2.1, steps 2 to 4) ------------------------


@dataclasses.dataclass(frozen=True)
class Rejection:
    """A needle a builder output already holds: its class, the inspection that
    found it and the file — never the value — and what to redraw."""

    needle_class: str  # "value", "row_count", "calendar", "label"
    inspection: str
    file: str
    keys: tuple[Key, ...] = ()


class DrawExhausted(Exception):
    """No clean draw within the limit: a harness limitation that withholds every
    verdict (§2.5.4), never a failure of a candidate."""

    def __init__(self, record: dict):
        self.record = record
        last = record["rejections"][-1] if record["rejections"] else {}
        super().__init__(f"draw exhausted after {record['draws']} draws; last: {last}")


def provenance(fx: Fixture) -> dict[str, list[tuple[str, tuple[Key, ...]]]]:
    """Each canonical value the needles come from → every (class, cells to
    redraw) it is: a value can be a count and the row count at once
    (PROTO-1-09). Texts that are fixed labels have no cell; the calendar and
    the row count are classes of their own."""
    out: dict[str, list[tuple[str, tuple[Key, ...]]]] = defaultdict(list)
    by_value: dict[str, list[Key]] = defaultdict(list)
    for key, m in fx.cells.items():
        for v in (m.order_count, m.unit_count, m.gross, m.discount, m.net):
            by_value[str(v)].append(key)
    for (f, i, root), (net, units) in summary(fx).items():
        cell = tuple(k for k in fx.cells if k[0] == i and ROOT_OF[k[2]] == root and _in_filter(k[1], f))
        for v in (net, units):
            by_value[str(v)].extend(cell)
    rows = fx.rows()
    for name in contract().reports[REPORT].sums:
        by_value[str(sum((r[COLUMNS.index(name)] for r in rows), ZERO if "amount" in name else 0))].extend(fx.cells)
    for value, keys in by_value.items():
        out[value].append(("value", tuple(sorted(dict.fromkeys(keys)))))
    for i in range(MONTHS):
        y, _ = fx.month(i)
        for text in (fx.year_month(i), str(y)):
            if ("calendar", ()) not in out[text]:
                out[text].append(("calendar", ()))
    out[str(len(fx.cells))].append(("row_count", ()))
    for label in (*CHANNELS, *CHANNELS.values(), *ROOTS, *ROOT_OF):
        out[label].append(("label", ()))
    return dict(out)


class DrawStopped(Exception):
    """The collision search could not read a builder output: the draw stops
    with the file and the reason, a harness limitation (PROTO-1-07)."""

    def __init__(self, reasons: list[dict], record: dict | None = None):
        self.reasons, self.record = reasons, record
        super().__init__(f"the draw stopped: {reasons[:3]}")


def draw(seed: int, collides, limit: int = DRAWS_MAX) -> tuple[Fixture, dict]:
    """Steps 2 to 4 of §2.1. `collides(fx)` searches both builder outputs with
    both inspections and returns the rejections; a colliding value is redrawn,
    a colliding row count changes *k*, a colliding calendar moves the window.
    Raises `DrawExhausted` with the record when no draw within `limit` is
    clean."""
    if not 1 <= limit <= DRAWS_MAX:
        raise ValueError(f"a draw takes at most {DRAWS_MAX} draws (§2.1)")
    fx, d = generate(seed)
    record: dict = {"seed": seed, "draws": 0, "rejections": []}
    tried_k = {fx.k}
    while record["draws"] < limit:
        record["draws"] += 1
        try:
            found = collides(fx)
        except DrawStopped as stopped:
            record["stopped"] = stopped.reasons
            raise DrawStopped(stopped.reasons, record) from None
        # One order whatever the process's hashing, so that a seed gives one fixture (PROTO-1-09).
        found = sorted(set(found), key=lambda r: (r.needle_class, r.inspection, r.file, r.keys))
        if not found:
            record["fixture"] = fx.describe()
            return fx, record
        record["rejections"] += [{"draw": record["draws"], "class": r.needle_class, "inspection": r.inspection, "file": r.file}
                                 for r in found]
        classes = {r.needle_class for r in found}
        if "label" in classes:
            break  # a fixed label cannot be redrawn
        if "calendar" in classes:
            fx = _moved(fx, d)
        if "row_count" in classes:
            fresh = [k for k in K_VALUES if k not in tried_k]
            if not fresh:
                break
            fx = _with_k(fx, d, d.rng.choice(fresh))
            tried_k.add(fx.k)
        for r in found:
            keys = sorted(k for k in r.keys if k in fx.cells)  # a new k replaces the last month's cells
            if r.needle_class == "value" and keys:
                _redraw(fx, d, d.rng.choice(keys))
        _separate_order_sums(fx, d)
    raise DrawExhausted(record)


def _moved(fx: Fixture, d: _Draw) -> Fixture:
    start = fx.start
    while start == fx.start:
        start = d.start()
    return Fixture(fx.seed, start, fx.k, fx.partial, fx.cells, fx.mutant)


def _with_k(fx: Fixture, d: _Draw, k: int) -> Fixture:
    """The same values everywhere but the last month, which gets k groups."""
    cells = {key: m for key, m in fx.cells.items() if key[0] != PARTIAL}
    for key, m in fx.cells.items():
        if key[0] == PARTIAL:
            d.release(m)
    out = Fixture(fx.seed, fx.start, k, d.partial(k), cells, fx.mutant)
    for channel, root in out.partial:
        _fill(out, d, PARTIAL, channel, root)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("write", help="draw a fixture from a seed and write it, its Parquet and its package")
    w.add_argument("--seed", type=int, required=True)
    w.add_argument("--out", type=pathlib.Path, required=True)
    w.add_argument("--mutant", action="store_true", help="the G mutant of that fixture")
    args = parser.parse_args(argv)
    fx, _ = generate(args.seed)
    if args.mutant:
        fx = mutant(fx)
    print(json.dumps(write(fx, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
