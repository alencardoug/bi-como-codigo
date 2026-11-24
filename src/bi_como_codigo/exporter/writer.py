"""§7: the Parquet written by DuckDB from exact bindings, and read back.

The writer takes a copy of the frozen rows and hands every cell to DuckDB as
exact text: a JSON Lines file in the private run directory, read with every
column declared VARCHAR — no type is inferred — then cast explicitly to the
report contract's type. Decimals are their fixed-point strings, cast to
DECIMAL(p,s), never `Decimal` parameters, which DuckDB infers as DOUBLE
(EXP-1-04); instants are integer microseconds, built as
`make_timestamp(us)::TIMESTAMPTZ` under DuckDB's time zone set to UTC, and
read back as `epoch_us`, never fetched as `datetime` (EXP-1-05). JSON keeps a
null apart from an empty text. A file, not `executemany`: binding row by row
took 47 s for 5,775 rows of 17 columns on this machine, the file 0.2 s (§16).

The locked DuckDB reads Parquet from a path only (EXP-2-04), so the written
file is retained as bytes, written to a new file opened exclusively, read from
there with the path bound as a parameter, and checked against the retained
digest after the read.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re

from .. import contract as c
from . import PATH_REFUSED, READBACK_TAMPERED, ROUND_TRIP, WRITE_FAILED, Refused
from .views import View

#: The writer's options, fixed (§7).
COMPRESSION = "zstd"
ROW_GROUP_SIZE = 122_880
MEMORY_LIMIT = "512MB"
_SAFE = re.compile(r"[A-Za-z0-9._/-]+")  # §10: the path is interpolated into SQL


def _safe(path: pathlib.Path) -> str:
    text = path.as_posix()
    if not _SAFE.fullmatch(text):
        raise Refused(PATH_REFUSED, check="characters")
    return text


def connect(run_dir: pathlib.Path, memory_limit: str = MEMORY_LIMIT):
    """DuckDB in a database file inside the private run directory, its
    `temp_directory` there too, no extension loaded, one thread, UTC."""
    import duckdb

    con = duckdb.connect(_safe(run_dir / "export.duckdb"), config={
        "autoinstall_known_extensions": False,
        "autoload_known_extensions": False,
        "threads": 1,
        "memory_limit": memory_limit,
        "temp_directory": _safe(run_dir / "duckdb.tmp"),
    })
    con.execute("SET TimeZone = 'UTC'")  # make_timestamp(us)::TIMESTAMPTZ reads the session's zone
    con.execute("SET lock_configuration = true")
    if con.execute("SELECT current_setting('TimeZone')").fetchone()[0] != "UTC":
        raise Refused(WRITE_FAILED, check="time_zone")
    return con


def _q(name: str) -> str:
    return '"' + name + '"'  # names come from the strict contract


def _cast(col, export_type: str, expr: str) -> str:
    """The explicit cast of one VARCHAR cell to the contract's type."""
    if col.is_instant:
        return f"CAST(make_timestamp(CAST({expr} AS BIGINT)) AS TIMESTAMPTZ)"
    return f"CAST({expr} AS {export_type})"


def _cell(col, value) -> str | None:
    """A frozen cell as exact text: decimals are already their fixed-point
    strings, integers and instants their digits, booleans `true` or `false`."""
    if value is None:
        return None
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if type(value) is str:
        return value
    raise Refused(WRITE_FAILED, check="cell")


def create_table(con, view: View, report: c.Report) -> str:
    table = "r_" + view.view
    columns = ", ".join(f"{_q(col.name)} {report.column(col.name).type}" for col in view.columns)
    con.execute(f"CREATE TABLE {_q(table)} ({columns})")
    return table


def insert(con, table: str, view: View, report: c.Report, rows: list[tuple], *, run_dir: pathlib.Path) -> None:
    if not rows:
        return
    path = run_dir / f"{view.report}.rows.jsonl"
    with open(path, "x", encoding="utf-8") as f:
        for row in rows:
            cells = {col.name: _cell(col, value) for col, value in zip(view.columns, row)}
            f.write(json.dumps(cells, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")
    spec = "{" + ", ".join(f"'{col.name}': 'VARCHAR'" for col in view.columns) + "}"
    select = ", ".join(_cast(col, report.column(col.name).type, _q(col.name)) for col in view.columns)
    con.execute(
        f"INSERT INTO {_q(table)} SELECT {select} FROM read_json(?, format = 'newline_delimited', columns = {spec})",
        [_safe(path)],
    )


def copy_out(con, table: str, path: pathlib.Path) -> None:
    con.execute(
        f"COPY {_q(table)} TO '{_safe(path)}' (FORMAT parquet, COMPRESSION {COMPRESSION}, ROW_GROUP_SIZE {ROW_GROUP_SIZE})"
    )


def write(con, run_dir: pathlib.Path, view: View, report: c.Report, rows: list[tuple]) -> pathlib.Path:
    """The copy of the reference into a table of the report contract's types,
    then Parquet in the run directory. Returns the written file."""
    path = run_dir / f"{view.report}.written.parquet"
    try:
        table = create_table(con, view, report)
        insert(con, table, view, report, rows, run_dir=run_dir)
        copy_out(con, table, path)
    except Refused:
        raise
    except Exception as exc:
        raise Refused(WRITE_FAILED, view.view, "write", type(exc).__name__) from None
    return path


def retain(path: pathlib.Path) -> tuple[bytes, str]:
    """§7, step 1: the written file as bytes — the retained buffer — and its SHA-256."""
    buffer = path.read_bytes()
    return buffer, hashlib.sha256(buffer).hexdigest()


def stage(buffer: bytes, path: pathlib.Path) -> None:
    """§7, step 2: the buffer written to a new file, opened exclusively."""
    with open(path, "xb") as f:
        f.write(buffer)


def select_back(view: View) -> str:
    parts = []
    for col in view.columns:
        if col.is_decimal:
            parts.append(f"CAST({_q(col.name)} AS VARCHAR)")
        elif col.is_instant:
            parts.append(f"epoch_us({_q(col.name)})")
        else:
            parts.append(_q(col.name))
    return f"SELECT {', '.join(parts)} FROM read_parquet(?)"


def describe_back(con, path: pathlib.Path) -> list[tuple[str, str]]:
    return [(row[0], row[1]) for row in con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [_safe(path)]).fetchall()]


def read_back(con, view: View, report: c.Report, path: pathlib.Path) -> list[tuple]:
    """§7, step 3: every column in the contract's order — decimals as their
    exact text, instants as `epoch_us` — with the path bound as a parameter."""
    try:
        schema = describe_back(con, path)
        rows = con.execute(select_back(view), [_safe(path)]).fetchall()
    except Refused:
        raise
    except Exception as exc:
        raise Refused(ROUND_TRIP, view.view, "read_back", type(exc).__name__) from None
    if schema != [(col.name, col.type) for col in report.columns]:
        raise Refused(ROUND_TRIP, view.view, "read_back")
    return [tuple(r) for r in rows]


def check_staged(path: pathlib.Path, retained_sha: str, view: str) -> None:
    """§7, step 4: after the read, the file read is the retained buffer."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != retained_sha:
        raise Refused(READBACK_TAMPERED, view, "read_back")
