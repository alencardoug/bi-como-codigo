"""How the package gate's value inspection meets a report page's own code
(docs/report_page.md §2). It builds the gate's own needles — the functions of
`bi_como_codigo.contract`, unchanged — from M59's capture of the 16 views,
outside Git, and searches them in the files given, by substring, as `verify`
does (docs/package_gate.md §6). For each hit it prints the kind, the length,
the view columns holding it and how many of its occurrences stand as a token —
not flanked by a letter, a digit or a non-ASCII byte, nor, for a number,
continued by a separator and a digit —, which is what a match by token would
still find. It never prints a value.

An approximation, stated: a value is the capture's CSV text, which for these
views is DuckDB's canonical text of the exported types; a sum is the sum of
the column at the column's largest scale. The authoritative search is
`verify`'s, on the exported package.

    uv run --frozen python evidence/20261125/collision_surface.py <capture folder> <file>...
"""

import csv
import datetime
import decimal
import pathlib
import re
import sys

from bi_como_codigo import contract as k

NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
GLUE = re.compile(rb"[A-Za-z0-9\x80-\xff]")
HASH = re.compile(rb"sha(256|384|512)-[A-Za-z0-9+/=]+")


def capture(folder: pathlib.Path) -> tuple[list[k.Values], dict[bytes, set[str]]]:
    values, origin = [], {}
    for f in sorted(folder.glob("*.csv")):
        rows = list(csv.DictReader(f.open(encoding="utf-8")))
        v = k.Values(f.stem, b"\x00")
        v.numbers.add(str(len(rows)))
        for col in rows[0]:
            cells = [r[col] for r in rows if r[col] != ""]
            for c in cells:
                origin.setdefault(c.encode("utf-8"), set()).add(f"{f.stem}.{col}")
            if cells and all(NUMBER.match(c) for c in cells):
                v.numbers.update(cells)
                scale = max(len(c.partition(".")[2]) for c in cells)
                v.numbers.add(f"{sum(decimal.Decimal(c) for c in cells):.{scale}f}")
            else:
                v.texts.update(cells)
        values.append(v)
    return values, origin


def tokens(data: bytes, needle: bytes) -> int:
    count = 0
    for m in re.finditer(re.escape(needle), data):
        a, b = m.start(), m.end()
        left, right = data[a - 1:a], data[b:b + 1]
        ok_left = not left or not GLUE.match(left)
        ok_right = not right or not GLUE.match(right)
        if ok_right and right in (b".", b",") and re.match(rb"\d", data[b + 1:b + 2]):
            ok_right = False
        if ok_left and left in (b".", b",", b"-") and re.match(rb"\d", data[a - 2:a - 1]):
            ok_left = False
        count += ok_left and ok_right
    return count


def main() -> None:
    values, origin = capture(pathlib.Path(sys.argv[1]))
    needles = [n for code, n in k.needles(values, set()) if code == k.CLEAR_VALUE]
    eligible = sum(1 for v in values for x in v.numbers if k.eligible_number(x))
    three = {str(i) for i in range(100, 1000)} & set().union(*(v.numbers for v in values))
    print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"views {len(values)}; eligible numbers {eligible}; value needles {len(needles)}; "
          f"three-digit integers that are a value somewhere: {len(three)} of 900")
    files_hit = token_hits = 0
    for name in sys.argv[2:]:
        path = pathlib.Path(name)
        data = path.read_bytes()
        hits = [n for n in needles if n in data]
        files_hit += bool(hits)
        spans = [m.span() for m in HASH.finditer(data)]
        print(f"{name}: {len(hits)} needle(s)")
        for n in hits:
            where = [m.start() for m in re.finditer(re.escape(n), data)]
            in_hash = all(any(a <= q < b for a, b in spans) for q in where)
            kind = "number" if re.fullmatch(rb"[-0-9.,]+", n) else "text"
            cols = sorted(origin.get(n, {"(a sum or another spelling)"}))
            t = tokens(data, n)
            token_hits += t > 0
            print(f"  {kind}, {len(n)} bytes, {len(where)} occurrence(s), {t} as a token"
                  f"{', all inside integrity hashes' if in_hash else ''}; from {', '.join(cols[:3])}"
                  f"{f' and {len(cols) - 3} more' if len(cols) > 3 else ''}")
    print(f"files with a hit: {files_hit} of {len(sys.argv) - 2}; hits that stand as a token somewhere: {token_hits}")


if __name__ == "__main__":
    main()
