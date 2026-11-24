"""How the exporter's writer hands rows to DuckDB 1.5.6 (docs/exporter.md §16): row by row with
`executemany` and an explicit cast, against one JSON Lines file read with every column VARCHAR and
cast after. Invented decimals, the size of M59's largest view — 5,775 rows — with 17 columns of
DECIMAL(12,2). Prints the seconds of each and whether both tables are equal.

    uv run --frozen python evidence/20261124/writer_load.py
"""
import datetime
import json
import pathlib
import random
import tempfile
import time

import duckdb

ROWS, COLS = 5775, 17
rng = random.Random(20261124)
rows = [[f"{rng.randint(0, 10**9) / 100:.2f}" for _ in range(COLS)] for _ in range(ROWS)]
rows[0][0] = None
print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), f"duckdb {duckdb.__version__}, {ROWS} rows x {COLS} DECIMAL(12,2)")
con = duckdb.connect(":memory:", config={"autoload_known_extensions": False, "autoinstall_known_extensions": False, "threads": 1})
ddl = ", ".join(f"c{i} DECIMAL(12,2)" for i in range(COLS))
con.execute(f"CREATE TABLE a ({ddl})")
con.execute(f"CREATE TABLE b ({ddl})")
t = time.monotonic()
con.executemany("INSERT INTO a VALUES (" + ", ".join("CAST(? AS DECIMAL(12,2))" for _ in range(COLS)) + ")", rows)
print(f"executemany, a cast per cell: {time.monotonic() - t:.2f} s")
with tempfile.TemporaryDirectory() as d:
    path = pathlib.Path(d) / "rows.jsonl"
    t = time.monotonic()
    with open(path, "x", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({f"c{i}": v for i, v in enumerate(r)}, separators=(",", ":")) + "\n")
    spec = "{" + ", ".join(f"'c{i}': 'VARCHAR'" for i in range(COLS)) + "}"
    select = ", ".join(f"CAST(c{i} AS DECIMAL(12,2))" for i in range(COLS))
    con.execute(f"INSERT INTO b SELECT {select} FROM read_json(?, format = 'newline_delimited', columns = {spec})", [str(path)])
    print(f"JSON Lines, every column VARCHAR, cast after: {time.monotonic() - t:.2f} s")
print("equal:", con.execute("SELECT count(*) FROM (SELECT * FROM a EXCEPT ALL SELECT * FROM b)").fetchone()[0] == 0
      and con.execute("SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM a)").fetchone()[0] == 0)
