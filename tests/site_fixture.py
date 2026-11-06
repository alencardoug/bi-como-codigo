"""Writes the fixture package into `site/package/` (docs/package_gate.md §8).

One small table per fixture report of `release/contract.json`, written as a
real Parquet file by DuckDB, with its control totals computed here in Python
with `decimal` — independently of the gate's DuckDB query (§3) — and sealed
by the envelope's producer under `release/profiles.json`. The values are
invented placeholders (`fixture_…`), not figures of eng_dados: no report data
reaches the repository before stage 2.4. Each run draws new keys, salts and
IVs, so its bytes differ every time.

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

#: The fixture rows, in the contract's column order. Chosen to exercise every
#: check: a decimal and an integer sum, a nullable column with a null, a
#: two-column grain, a date, a wide decimal that is not summed, a boolean.
ROWS: dict[str, list[tuple]] = {
    "P01": [
        ("fixture_a", Decimal("1.25"), 2),
        ("fixture_b", Decimal("3.50"), None),
        ("fixture_c", Decimal("10.00"), 7),
        ("fixture_d", Decimal("-0.75"), 1),
    ],
    "P02": [
        (dt.date(2025, 1, 1), "fixture_loja", 1200),
        (dt.date(2025, 1, 1), "fixture_app", 340),
        (dt.date(2025, 2, 1), "fixture_loja", 1105),
    ],
    "P13": [
        ("fixture_norte", 120, Decimal("0.1250"), True),
        ("fixture_sul", 85, None, False),
    ],
}


def parquet(report: c.Report, rows: list[tuple], types: dict[str, str] | None = None) -> bytes:
    """The rows as a Parquet file written by DuckDB, with the contract's
    types — or others, for a mutation."""
    import duckdb

    types = types or {}
    columns = [(col.name, types.get(col.name, col.type)) for col in report.columns]
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE t (" + ", ".join(f'"{n}" {t}' for n, t in columns) + ")")
    if rows:
        con.executemany("INSERT INTO t VALUES (" + ", ".join("?" for _ in columns) + ")", rows)
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "t.parquet"
        con.execute(f"COPY t TO '{path.as_posix()}' (FORMAT parquet)")
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


def payloads(contract: c.Contract) -> dict[str, tuple[bytes, bytes]]:
    return {rid: (totals(contract, report, ROWS[rid]), parquet(report, ROWS[rid])) for rid, report in contract.reports.items()}


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
