"""Writes the invented package into `site/package/` (docs/package_gate.md §8,
docs/exporter.md §11, N109).

One small table per report of `release/contract.json` — the 16 reports'
real shapes since stage 2.4's migration —, its rows **invented** from the
contract's types alone, written as a real Parquet file by DuckDB, with its
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


def rows_of(contract: c.Contract) -> dict[str, list[tuple]]:
    return {rid: invent(report) for rid, report in contract.reports.items()}


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
