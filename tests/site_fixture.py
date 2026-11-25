"""Writes the invented package into `site/package/` (docs/package_gate.md §8,
docs/exporter.md §11, N109).

One small table per report of `release/contract.json` — the 16 reports'
real shapes since stage 2.4's migration —, its rows **invented** from the
contract's types alone — P01's a grid with the shape of a chart, for the
report page's checks (`p01_rows`, docs/report_page.md §4) —, written as a real Parquet file by DuckDB, with its
control totals computed here in Python with `decimal`, independently of the
gate's DuckDB query (§3), and sealed by the envelope's producer under
`release/profiles.json`. No figure of eng_dados: every text is `fixture_…`,
every number made up. Each run draws new keys, salts and IVs, so its bytes
differ every time; the rows are the same every time.

    uv run --frozen python tests/site_fixture.py

The tests build their mutations from the same functions.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import pathlib
import shutil
import sys
import tempfile
from decimal import Decimal, localcontext

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.append(str(ROOT / "src"))

from bi_como_codigo import contract as c, envelope as e, release  # noqa: E402

OUT = ROOT / "site" / "package"
ROWS_PER_REPORT = 4


def invent(report: c.Report, count: int = ROWS_PER_REPORT) -> list[tuple]:
    """`count` rows of the report's shape, from its types alone. Texts are
    `fixture_<report>_<column>_<row>`, unique per row, so the grain holds;
    integers out of the grain have five digits from 12000 — a Brazilian
    spelling (`12.000`), and never a year the site's text cites, such as
    2026; decimals fit their precision; a nullable column is null in the
    second row."""
    rows = []
    for i in range(count):
        row = []
        for j, col in enumerate(report.columns):
            in_grain = col.name in report.grain
            if col.nullable and i == 1:
                row.append(None)
            elif col.type == "VARCHAR":
                row.append(f"fixture_{report.id.lower()}_{j}_{i}")
            elif col.type in ("SMALLINT", "INTEGER", "BIGINT"):
                row.append(i + 1 if in_grain else 12000 + 100 * j + 7 * i)
            elif col.decimal:
                precision, scale = col.decimal
                whole = ((i + 1) * (j + 2)) % 10 ** min(3, precision - scale) if precision > scale else 0
                fraction = f".{(7 * i + 3 * j + 1) % 10 ** scale:0{scale}d}" if scale else ""
                row.append(Decimal(f"{whole}{fraction}"))
            elif col.type == "BOOLEAN":
                row.append(i % 2 == 0)
            elif col.type == "TIMESTAMP WITH TIME ZONE":
                row.append(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(days=i, hours=j))
            elif col.type == "DATE":
                row.append(dt.date(2025, 1, 1) + dt.timedelta(days=i))
            else:  # pragma: no cover - a type the contract does not use
                raise ValueError(col.type)
        rows.append(tuple(row))
    return rows


def _param(value):
    """DuckDB infers DOUBLE for a `Decimal` parameter (EXP-1-04) and needs pytz
    for an aware `datetime`: both go as text, cast by the column's type."""
    if isinstance(value, Decimal):
        return f"{value:f}"
    if isinstance(value, dt.datetime):
        return value.isoformat()
    return value


def parquet(report: c.Report, rows: list[tuple], types: dict[str, str] | None = None, options: str = "") -> bytes:
    """The rows as a Parquet file written by DuckDB, with the contract's
    types — or others, for a mutation."""
    import duckdb

    types = types or {}
    columns = [(col.name, types.get(col.name, col.type)) for col in report.columns]
    con = duckdb.connect(":memory:")
    con.execute("SET TimeZone = 'UTC'")
    con.execute("CREATE TABLE t (" + ", ".join(f'"{n}" {t}' for n, t in columns) + ")")
    if rows:
        con.executemany("INSERT INTO t VALUES (" + ", ".join("?" for _ in columns) + ")", [[_param(v) for v in r] for r in rows])
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "t.parquet"
        con.execute(f"COPY t TO '{path.as_posix()}' (FORMAT parquet{', ' + options if options else ''})")
        return path.read_bytes()


def totals(contract: c.Contract, report: c.Report, rows: list[tuple]) -> bytes:
    """§3, independently of DuckDB: Python's `decimal` at 60 digits."""
    names = [col.name for col in report.columns]
    sums = {}
    with localcontext() as ctx:
        ctx.prec = 60
        for name in report.sums:
            scale = report.column(name).scale
            total = sum((Decimal(r[names.index(name)]) for r in rows if r[names.index(name)] is not None), Decimal(0))
            text = f"{total.quantize(Decimal(1).scaleb(-scale)):f}" if scale else str(int(total))
            sums[name] = "0" + text[2:] if text.startswith("-0") and Decimal(text) == 0 else text
    return c.totals_object(contract, report, len(rows), sums)


#: P01's invented grid (docs/report_page.md §4): fourteen months, the last partial;
#: three channels; four root categories of two categories each.
P01_MONTHS = [(2150, m) for m in range(1, 13)] + [(2151, 1), (2151, 2)]
P01_CHANNELS = [("fixture_canal_a", "fixture_tipo_loja"), ("fixture_canal_b", "fixture_tipo_site"), ("fixture_canal_c", "fixture_tipo_app")]
P01_ROOTS = [f"fixture_raiz_{k}" for k in range(1, 5)]


def p01_absent(i: int, c: int, k: int, j: int) -> bool:
    """The cells with no row, each a case the chart and the tables must show:
    the third channel has no row in the last month (its axis keeps the month);
    the third root has none under the third channel in the third month (a G
    under that filter only); the fourth root has none in the sixth month (a G
    under every filter, so its line breaks under `todos` too); and the second
    category of the second root is absent under the second channel in the fifth
    month, where the first sums to zero (a Z)."""
    last = len(P01_MONTHS) - 1
    return (c == 2 and i == last) or (k == 2 and c == 2 and i == 2) or (k == 3 and i == 5) or (k == 1 and c == 1 and i == 4 and j == 1)


def p01_rows(report: c.Report) -> list[tuple]:
    """P01 with the shape of a chart, from invented values only: amounts of five
    digits with cents, the partial month's an eighth of the others; integers
    out of the grain of five digits from 12000, as `invent`'s."""
    assert [col.name for col in report.columns] == [
        "year_month", "year_number", "month_number", "sales_channel_name", "channel_type", "root_category_name",
        "category_name", "order_count", "unit_count", "gross_revenue_amount", "discount_amount", "net_revenue_amount",
    ], "P01's columns changed: the invented grid follows them"
    rows = []
    last = len(P01_MONTHS) - 1
    for i, (year, month) in enumerate(P01_MONTHS):
        for c_, (channel, kind) in enumerate(P01_CHANNELS):
            for k, root in enumerate(P01_ROOTS):
                for j in range(2):
                    if p01_absent(i, c_, k, j):
                        continue
                    spread = int(hashlib.sha256(f"{i},{c_},{k},{j}".encode()).hexdigest()[:8], 16)  # deterministic, uncorrelated
                    whole = 10000 + spread % 80000
                    if i == last:
                        whole = 10000 + whole % 1250
                    net = Decimal(f"{whole}.{(i * 7 + c_ * 3 + k + j) % 100:02d}")
                    if k == 1 and c_ == 1 and i == 4:
                        net = Decimal("0.00")  # the Z: a cell whose rows sum to zero
                    discount = Decimal(f"{1000 + (i + c_ + k + j) % 900}.{(i * 3 + j) % 100:02d}")
                    rows.append((
                        f"{year}-{month:02d}", year, month, channel, kind, root, f"{root}_cat_{j + 1}",
                        12000 + (i * 97 + c_ * 13 + k * 11 + j * 5) % 5000, 12000 + (i * 131 + c_ * 17 + k * 29 + j * 7) % 7000,
                        net + discount, discount, net,
                    ))
    return rows


def rows_of(contract: c.Contract) -> dict[str, list[tuple]]:
    return {rid: p01_rows(report) if rid == "P01" else invent(report) for rid, report in contract.reports.items()}


#: The rows of the committed contract, by report.
ROWS: dict[str, list[tuple]] = rows_of(c.load(ROOT)[0])


def payloads(contract: c.Contract) -> dict[str, tuple[bytes, bytes]]:
    rows = rows_of(contract)
    return {rid: (totals(contract, report, rows[rid]), parquet(report, rows[rid])) for rid, report in contract.reports.items()}


def main() -> int:
    declared = release.profiles(ROOT)
    contract, _ = c.load(ROOT)
    manifest, files = e.encrypt_package(declared, payloads(contract))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (OUT / name).write_bytes(data)
    print(f"wrote {OUT.relative_to(ROOT)}: manifest.json and {len(files)} envelope(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
